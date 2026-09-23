"""`POST /api/v1/chat/ask` — viết lại câu hỏi, tìm kiếm hybrid song song cho từng câu hỏi con, sinh và
kiểm `claims[]` (2-D mở rộng). Yêu cầu đã đăng nhập (Phase 4).

Kế hoạch: docs/chatbot-vsf/plan/phase-2/2-c-2-d-tim-kiem-va-tra-loi-ke-hoach-chi-tiet.md
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Annotated, Literal, cast
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import (
    get_chat_completion_port,
    get_chat_throttle,
    get_current_user,
    get_db,
    get_embedding_port,
    get_langfuse_tracer,
    get_session_factory,
)
from src.config import Settings, get_settings
from src.dto.request.chat_request_dto import ChatAskRequestDTO
from src.dto.response.chat_response_dto import ChatAskResponseDTO, ClaimResponseDTO, SourceResponseDTO
from src.dto.response.document_content_response_dto import DocumentContentResponseDTO
from src.dto.response.error_response_dto import ErrorResponseDTO
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.model.document import Document
from src.model.document_version import DocumentVersion
from src.model.user import User
from src.services.auth.errors import AuthError
from src.services.chat.answer_service import Claim, QuestionEvidence, answer_with_claims
from src.services.chat.chat_throttle import ChatThrottle
from src.services.chat.query_rewrite import rewrite_query
from src.services.chat.validator import validate_claims
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.lexical import to_lexical_text
from src.services.retrieval.hybrid_search import SectionEvidence, search_to_sections

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def _evidence_for_question(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    question: str,
    query_vector: list[float],
    as_of: date,
    model_version: str,
) -> QuestionEvidence:
    # Mỗi câu hỏi con mở session riêng — chạy song song (asyncio.gather) trên MỘT AsyncSession dùng chung
    # không an toàn (SQLAlchemy không cho nhiều truy vấn đồng thời trên cùng session).
    async with session_factory() as session:
        sections = await search_to_sections(
            session,
            lexical_query=to_lexical_text(question),
            query_vector=query_vector,
            as_of=as_of,
            model_version=model_version,
        )
    return QuestionEvidence(question=question, sections=sections)


def _resolve_source(claim: Claim, section_by_chunk: dict[int, SectionEvidence]) -> SourceResponseDTO | None:
    if claim.response_type != "ANSWER" or claim.chunk_id is None:
        return None
    section = section_by_chunk.get(claim.chunk_id)
    if section is None:
        return None
    return SourceResponseDTO(
        document_title=section.document_title,
        version_label=section.version_label,
        section_heading=section.heading,
        document_url=section.document_url,
        version_id=section.version_id,
    )


@router.post(
    "/ask",
    response_model=ChatAskResponseDTO,
    responses={401: {"model": ErrorResponseDTO}, 429: {"model": ErrorResponseDTO}},
)
async def ask(
    body: ChatAskRequestDTO,
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    embedding: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    llm: Annotated[ChatCompletionPort, Depends(get_chat_completion_port)],
    tracer: Annotated[LangfuseTracer, Depends(get_langfuse_tracer)],
    throttle: Annotated[ChatThrottle, Depends(get_chat_throttle)],
) -> ChatAskResponseDTO:
    # Endpoint tốn tiền thật (LLM + embedding) mỗi lần gọi — chặn lạm dụng/vòng lặp lỗi trước khi làm gì khác.
    wait = throttle.retry_after(user.id)
    if wait > 0:
        raise AuthError(429, "TOO_MANY_QUESTIONS", "chat.too_many_questions", headers={"Retry-After": str(wait)})
    throttle.record_question(user.id)

    as_of = body.as_of or _today(settings.app_timezone)

    # 0. Viết lại/tách câu hỏi (mục 5, kế hoạch) — không lưu vào DB, chỉ dùng tạm cho lượt này (mục 12).
    with tracer.span("rewrite_query", metadata={"input_length": len(body.question)}) as span:
        questions = await rewrite_query(body.question, llm)
        span.update(output={"question_count": len(questions)})
    if not questions:
        return ChatAskResponseDTO(claims=[])

    # 1. Embed TẤT CẢ câu hỏi con trong 1 lần gọi (batch, tiết kiệm hơn N lần gọi riêng).
    with tracer.span("embed_questions", metadata={"question_count": len(questions)}):
        vectors = await embedding.embed(questions)
    model_version = embedding.model_version

    # 2. Tìm kiếm hybrid SONG SONG cho từng câu hỏi con (mục 12.3, kế hoạch — không tuần tự).
    with tracer.span("retrieval", metadata={"question_count": len(questions)}) as span:
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
        span.update(output={"section_counts": [len(item.sections) for item in items]})

    # 3. Một lời gọi LLM duy nhất trả claims[] cho toàn bộ câu hỏi con.
    with tracer.span("llm_answer", metadata={"question_count": len(questions)}) as span:
        claims = await answer_with_claims(items, llm)
        span.update(output={"claim_count": len(claims)})

    # 4. Kiểm từng claim (INV6/INV13) trước khi trả về — ép NO_BASIS nếu không qua kiểm tra.
    with tracer.span("validate_claims") as span:
        validated = validate_claims(claims, items)
        span.update(output={"answer_count": sum(1 for c in validated if c.response_type == "ANSWER")})

    section_by_chunk = {cid: section for item in items for section in item.sections for cid in section.chunk_ids}
    return ChatAskResponseDTO(
        claims=[
            ClaimResponseDTO(
                question=claim.question,
                response_type=cast(Literal["ANSWER", "NO_BASIS"], claim.response_type),
                reason_code=claim.reason_code,
                text=claim.text,
                quote=claim.quote,
                source=_resolve_source(claim, section_by_chunk),
            )
            for claim in validated
        ]
    )


def _today(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


@router.get(
    "/documents/{version_id}",
    response_model=DocumentContentResponseDTO,
    responses={401: {"model": ErrorResponseDTO}, 404: {"model": ErrorResponseDTO}},
)
async def get_document(
    version_id: int,
    _user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentContentResponseDTO:
    """Nội dung Markdown đầy đủ của một `document_version` — FE hiện trong modal, cuộn tới đúng section đã
    trích dẫn thay vì bắt người dùng tải file gốc rồi tự tìm (chỉ trả cho người đã đăng nhập, cùng mức truy
    cập với `/chat/ask` — không thêm kiểm tra `confidentiality` riêng vì người dùng đã nhận đúng section này
    làm nguồn trích dẫn từ một câu trả lời họ được phép thấy).
    """
    row = (
        await session.execute(
            select(DocumentVersion.markdown, DocumentVersion.version_label, Document.title)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(DocumentVersion.id == version_id)
        )
    ).one_or_none()
    if row is None:
        raise AuthError(404, "DOCUMENT_NOT_FOUND", "chat.document_not_found")
    markdown, version_label, title = row
    return DocumentContentResponseDTO(document_title=title, version_label=version_label, markdown=markdown)
