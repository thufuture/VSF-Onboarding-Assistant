"""Pipeline hỏi đáp tài liệu dùng chung: viết lại câu hỏi -> embedding -> tìm hybrid song song -> sinh `claims[]` -> kiểm chứng.

Tách khỏi `chat_router` để cả `/chat/ask` (HR, Admin) và Viga của nhân viên (`services/viga`) chạy đúng một đường, có
cùng các bước đo Langfuse (chỉ số liệu, không nội dung — INV8).

Lịch sử hội thoại (nếu có) **chỉ** đi vào bước viết lại câu hỏi để hiểu câu nối tiếp ("còn thử việc thì sao?"); không bao
giờ đi vào bước tìm kiếm hay trích dẫn, nên câu trả lời trước không thể bị coi là bằng chứng cho câu sau (mục 6.2).
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.call_metrics import Collected, call_context, collect_calls
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.lexical import to_lexical_text
from src.services.retrieval.hybrid_search import SectionEvidence, search_to_sections
from src.services.viga.answer_service import Claim, QuestionEvidence, answer_with_claims
from src.services.viga.query_rewrite import rewrite_query
from src.services.viga.validator import validate_claims


@dataclass(frozen=True)
class DocumentQaResult:
    claims: list[Claim]
    section_by_chunk: dict[int, SectionEvidence]


def usage_summary(used: Collected) -> dict[str, Any]:
    """Tổng token/chi phí/độ trễ của các lời gọi trong một bước, gắn vào span cha (từng lời gọi đã có generation riêng)."""
    if not used.calls:
        return {}
    return {
        "model": used.model,
        "prompt_tokens": used.prompt_tokens,
        "completion_tokens": used.completion_tokens,
        "latency_ms": round(used.latency_ms),
        "estimated_cost_usd": used.cost_usd,
    }


async def _evidence_for_question(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    question: str,
    query_vector: list[float],
    as_of: date,
    model_version: str,
) -> QuestionEvidence:
    # Mỗi câu hỏi con mở session riêng: chạy song song trên MỘT AsyncSession dùng chung không an toàn.
    async with session_factory() as session:
        sections = await search_to_sections(
            session,
            lexical_query=to_lexical_text(question),
            query_vector=query_vector,
            as_of=as_of,
            model_version=model_version,
        )
    return QuestionEvidence(question=question, sections=sections)


async def run_document_qa(
    question: str,
    *,
    llm: ChatCompletionPort,
    embedding: EmbeddingPort,
    session_factory: async_sessionmaker[AsyncSession],
    tracer: LangfuseTracer,
    as_of: date,
    history: Sequence[tuple[str, str]] | None = None,
) -> DocumentQaResult:
    # Gốc của trace khi gọi từ chat/ticket; nằm trong "viga.ask" khi gọi từ Viga.
    with tracer.span("document_qa", input=question, metadata={"input_length": len(question)}) as root:
        result = await _run_document_qa(
            question,
            llm=llm,
            embedding=embedding,
            session_factory=session_factory,
            tracer=tracer,
            as_of=as_of,
            history=history,
        )
        root.update(
            output={
                "answers": [c.text for c in result.claims if c.response_type == "ANSWER"],
                "types": [c.response_type for c in result.claims],
            }
        )
    return result


async def _run_document_qa(
    question: str,
    *,
    llm: ChatCompletionPort,
    embedding: EmbeddingPort,
    session_factory: async_sessionmaker[AsyncSession],
    tracer: LangfuseTracer,
    as_of: date,
    history: Sequence[tuple[str, str]] | None,
) -> DocumentQaResult:
    # 0. Viết lại/tách câu hỏi (mục 5, kế hoạch). Không lưu kết quả viết lại vào DB.
    with tracer.span("rewrite_query", input={"question": question, "history_turns": len(history or [])}) as span:
        questions = await rewrite_query(question, llm, history=history)
        span.update(output={"questions": questions, "question_count": len(questions)})
    if not questions:
        return DocumentQaResult(claims=[], section_by_chunk={})

    # 1. Embed TẤT CẢ câu hỏi con trong một lần gọi.
    with tracer.span("embed_questions", input=questions, metadata={"question_count": len(questions)}) as span:
        with call_context(operation="chat.embed"):
            vectors = await embedding.embed(questions)
        span.update(output={"vectors": len(vectors), "dimensions": len(vectors[0]) if vectors else 0})
    model_version = embedding.model_version

    # 2. Tìm hybrid song song cho từng câu hỏi con.
    with tracer.span("retrieval", input=questions, metadata={"question_count": len(questions)}) as span:
        items = list(
            await asyncio.gather(
                *(
                    _evidence_for_question(
                        session_factory, question=q, query_vector=v, as_of=as_of, model_version=model_version
                    )
                    for q, v in zip(questions, vectors, strict=True)
                )
            )
        )
        span.update(
            output={
                "section_counts": [len(item.sections) for item in items],
                "sections": [[s.heading for s in item.sections] for item in items],
            }
        )

    # 3. Một lời gọi LLM duy nhất trả claims[] cho toàn bộ câu hỏi con.
    with (
        tracer.span("llm_answer", metadata={"question_count": len(questions)}) as span,
        collect_calls() as used,
    ):
        claims = await answer_with_claims(items, llm)
        span.update(output={"claim_count": len(claims)}, metadata=usage_summary(used))

    # 4. Kiểm từng claim (INV6/INV13): ép NO_BASIS nếu không qua kiểm tra.
    with tracer.span("validate_claims", input={"claim_count": len(claims)}) as span:
        validated = validate_claims(claims, items)
        span.update(
            output={
                "answer_count": sum(1 for c in validated if c.response_type == "ANSWER"),
                "reasons": [c.reason_code for c in validated if c.reason_code],
            }
        )

    # 4b. Mô hình đôi khi trích sai một chữ rồi bị loại: thử lại đúng một lần, giữ kết quả có nhiều câu trả lời hơn.
    if any(c.reason_code == "validation_failed" for c in validated):
        with call_context(operation="chat.answer"):
            retry = validate_claims(await answer_with_claims(items, llm), items)
        if sum(c.response_type == "ANSWER" for c in retry) > sum(c.response_type == "ANSWER" for c in validated):
            validated = retry

    section_by_chunk = {cid: section for item in items for section in item.sections for cid in section.chunk_ids}
    return DocumentQaResult(claims=validated, section_by_chunk=section_by_chunk)
