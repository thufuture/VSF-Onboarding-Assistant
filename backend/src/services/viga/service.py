"""Điều phối một câu hỏi của nhân viên với Viga (flow chuẩn ở mục 17.2).

```text
 câu hỏi + conversation_id   (không có task_id: backend tự biết "việc hiện tại", mục 15.3e)
   [1] lưu câu hỏi vào hội thoại, đọc vài lượt gần nhất           (DB, không LLM)
   [2] ảnh chụp lộ trình của chính người hỏi                       (DB, không LLM)
   [3] bộ lọc thông tin cá nhân -> OUT_OF_SCOPE                     (luật, không LLM)
   [4] lối tắt luật cho 3 câu phổ biến                              (luật, không LLM)
   [5] LLM định tuyến: chọn công cụ trong danh sách đóng            (1 lần gọi LLM, code kiểm lại)
   [6] công cụ lộ trình (tất định) HOẶC pipeline tài liệu có kiểm chứng nguyên văn
   [7] không tra được -> NO_BASIS / OUT_OF_SCOPE / ERROR, kèm gợi ý "Gửi câu hỏi này cho HR"
```

Lùi dần, không bao giờ bỏ rơi người dùng: LLM định tuyến lỗi/sai -> hỏi đáp tài liệu; hỏi đáp tài liệu lỗi -> ERROR có thông báo
rõ và gợi ý gửi HR. Mọi câu hỏi kết thúc ở đúng một đường thoát.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.model.enums import ChatRole, GapKind
from src.model.user import User
from src.services.chat.pipeline import DocumentQaResult, run_document_qa
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.viga import conversations, gaps
from src.services.viga.guard import is_personal_info_question, shortcut_tool, tool_fits_question
from src.services.viga.router import CONFIDENCE_THRESHOLD, RouteDecision, route_question
from src.services.viga.snapshot import JourneySnapshot, load_snapshot
from src.services.viga.tools import (
    TASK_TOOLS,
    BlockingTask,
    SourceRef,
    SuggestedAction,
    ToolReply,
    clarify,
    explain_lock,
    no_journey,
    render,
    run_tool,
)

logger = logging.getLogger(__name__)

Route = str  # GUARD | SHORTCUT | LLM | DOCUMENTS | FALLBACK | NONE


@dataclass(frozen=True)
class SourceView:
    document_title: str
    version_label: str
    section_heading: str | None
    document_url: str
    version_id: int


@dataclass(frozen=True)
class ClaimView:
    question: str
    response_type: str  # ANSWER | NO_BASIS
    text: str | None
    quote: str | None
    source: SourceView | None


@dataclass
class VigaResult:
    conversation_id: int = 0
    message_id: int = 0
    new_conversation: bool = False
    response_type: str = "INFO"
    message: str = ""
    message_key: str | None = None
    message_params: dict[str, str | int] = field(default_factory=dict)
    claims: list[ClaimView] = field(default_factory=list)
    blocking_tasks: list[BlockingTask] = field(default_factory=list)
    actions: list[SuggestedAction] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    can_report: bool = False
    # Ý trong câu hỏi mà tài liệu chưa quy định, khi các ý còn lại đã trả lời được (đường thoát PARTIAL).
    unanswered: list[str] = field(default_factory=list)
    assumed_title: str | None = None
    route: Route = "NONE"

    def payload(self) -> dict[str, Any]:
        """Phần có cấu trúc lưu cùng tin nhắn để mở lại cuộc trò chuyện hiện đúng như lúc đã hỏi."""
        return {
            "message_key": self.message_key,
            "message_params": self.message_params,
            "claims": [vars(c) | {"source": vars(c.source) if c.source else None} for c in self.claims],
            "blocking_tasks": [vars(b) for b in self.blocking_tasks],
            "actions": [vars(a) for a in self.actions],
            "sources": [vars(s) for s in self.sources],
            "can_report": self.can_report,
            "unanswered": self.unanswered,
            "assumed_title": self.assumed_title,
            "route": self.route,
        }


def _from_tool(reply: ToolReply, route: Route) -> VigaResult:
    return VigaResult(
        response_type=reply.response_type,
        message=reply.message,
        message_key=reply.message_key,
        message_params=dict(reply.params),
        blocking_tasks=list(reply.blocking_tasks),
        actions=list(reply.actions),
        sources=list(reply.sources),
        assumed_title=reply.assumed_title,
        route=route,
    )


def _exit(response_type: str, key: str, route: Route, *, can_report: bool = False) -> VigaResult:
    return VigaResult(
        response_type=response_type, message=render(key), message_key=key, can_report=can_report, route=route
    )


def _source_view(chunk_id: int | None, section_by_chunk: dict[int, SectionEvidence]) -> SourceView | None:
    section = section_by_chunk.get(chunk_id) if chunk_id is not None else None
    if section is None:
        return None
    return SourceView(
        document_title=section.document_title,
        version_label=section.version_label,
        section_heading=section.heading,
        document_url=section.document_url,
        version_id=section.version_id,
    )


def _from_documents(result: DocumentQaResult, route: Route) -> VigaResult:
    claims = [
        ClaimView(
            question=claim.question,
            response_type=claim.response_type,
            text=claim.text,
            quote=claim.quote,
            source=_source_view(claim.chunk_id, result.section_by_chunk) if claim.response_type == "ANSWER" else None,
        )
        for claim in result.claims
    ]
    answers = [c for c in claims if c.response_type == "ANSWER" and c.text]
    if answers:
        # Nhiều ý cùng đáp án thì chỉ hiện một lần; ý không có căn cứ không hiện kèm khi đã có đáp án (chỉ gợi ý gửi HR).
        unique: list[ClaimView] = []
        for claim in answers:
            if not any(claim.text == seen.text and claim.quote == seen.quote for seen in unique):
                unique.append(claim)
        texts: list[str] = []
        for claim in unique:
            if claim.text and claim.text not in texts:
                texts.append(claim.text)
        return VigaResult(
            response_type="ANSWER",
            message=" ".join(texts),
            claims=unique,
            can_report=any(c.response_type != "ANSWER" for c in claims),
            unanswered=list(dict.fromkeys(c.question for c in claims if c.response_type != "ANSWER" and c.question)),
            route=route,
        )
    out_of_scope = any(claim.reason_code == "out_of_scope" for claim in result.claims)
    result_type, key = ("OUT_OF_SCOPE", "outOfScope") if out_of_scope else ("NO_BASIS", "noBasis")
    return VigaResult(
        response_type=result_type,
        message=render(key),
        message_key=key,
        claims=claims,
        can_report=True,
        route=route,
    )


async def _documents(
    question: str,
    *,
    llm: ChatCompletionPort | None,
    embedding: EmbeddingPort,
    session_factory: async_sessionmaker[AsyncSession],
    tracer: LangfuseTracer,
    today: date,
    history: list[tuple[str, str]],
    route: Route,
) -> VigaResult:
    if llm is None:
        return _exit("ERROR", "assistantUnavailable", route, can_report=True)
    try:
        result = await run_document_qa(
            question,
            llm=llm,
            embedding=embedding,
            session_factory=session_factory,
            tracer=tracer,
            as_of=today,
            history=history,
        )
    except Exception:
        # Đường lùi cuối: lỗi mạng tới LLM/embedding (hoặc lỗi khác) không bao giờ thành lỗi 500 cho nhân viên.
        logger.exception("viga_documents_failed")
        return _exit("ERROR", "assistantUnavailable", route, can_report=True)
    return _from_documents(result, route)


def _route_from_llm(
    decision: RouteDecision, snapshot: JourneySnapshot | None, question: str, now: datetime
) -> ToolReply | None:
    """Biến quyết định của LLM thành câu trả lời công cụ; `None` nghĩa là đi hỏi đáp tài liệu."""
    if snapshot is None:
        return None
    if decision.tool in TASK_TOOLS:
        if decision.unknown_task:
            return explain_lock(snapshot, None)  # việc nêu ra không thuộc lộ trình của người hỏi: NOT_IN_JOURNEY
        if decision.clarify:
            return clarify(snapshot.ready_tasks()[:3], decision.clarify)
    return run_tool(decision.tool, snapshot, question=question, args=decision.args, now=now)


async def _decide(
    question: str,
    *,
    snapshot: JourneySnapshot | None,
    history: list[tuple[str, str]],
    llm: ChatCompletionPort | None,
    embedding: EmbeddingPort,
    session_factory: async_sessionmaker[AsyncSession],
    tracer: LangfuseTracer,
    today: date,
    now: datetime,
) -> VigaResult:
    # [3] thông tin cá nhân không có trong tài liệu chung: thoát ngay, không tốn LLM.
    if is_personal_info_question(question):
        return _exit("OUT_OF_SCOPE", "outOfScope", "GUARD", can_report=True)

    # [4] lối tắt luật cho vài câu rất phổ biến và rõ ràng.
    shortcut = shortcut_tool(question)
    if shortcut is not None:
        if snapshot is None:
            return _from_tool(no_journey(), "SHORTCUT")
        return _from_tool(run_tool(shortcut, snapshot, question=question, args={}, now=now), "SHORTCUT")

    docs = dict(
        llm=llm,
        embedding=embedding,
        session_factory=session_factory,
        tracer=tracer,
        today=today,
        history=history,
    )
    # [5] LLM định tuyến; lỗi/sai/thiếu chắc chắn thì lùi về hỏi đáp tài liệu.
    decision = await route_question(question, llm, snapshot, history) if llm is not None else None
    if decision is None:
        return await _documents(question, route="FALLBACK", **docs)  # type: ignore[arg-type]
    if decision.tool == "none":
        return _exit("INFO", "smalltalk", "LLM")
    if decision.confidence < CONFIDENCE_THRESHOLD and not decision.clarify:
        return await _documents(question, route="FALLBACK", **docs)  # type: ignore[arg-type]
    if decision.tool == "search_documents":
        return await _documents(question, route="LLM", **docs)  # type: ignore[arg-type]

    if not decision.clarify and not tool_fits_question(decision.tool, question):
        # Công cụ lộ trình không hợp với câu hỏi (vd. hỏi thông tin trong tài liệu): tài liệu mới có đáp án đúng.
        return await _documents(question, route="FALLBACK", **docs)  # type: ignore[arg-type]

    # [6] công cụ lộ trình tất định.
    tool_reply = _route_from_llm(decision, snapshot, question, now)
    if tool_reply is None:
        if snapshot is None:
            return _from_tool(no_journey(), "LLM")
        return await _documents(question, route="FALLBACK", **docs)  # type: ignore[arg-type]
    return _from_tool(tool_reply, "LLM")


async def ask_viga(
    *,
    user: User,
    question: str,
    conversation_id: int | None,
    session_factory: async_sessionmaker[AsyncSession],
    embedding: EmbeddingPort,
    make_llm: Callable[[], ChatCompletionPort],
    tracer: LangfuseTracer,
    today: date,
    now: datetime | None = None,
) -> VigaResult:
    now = now or datetime.now(UTC)

    # [1] hội thoại: lưu câu hỏi trước (lỗi về sau vẫn còn trong lịch sử), đọc vài lượt gần nhất.
    async with session_factory() as session:
        new_conversation = conversation_id is None
        if conversation_id is None:
            conversation = await conversations.create_conversation(session, user, question)
            history: list[tuple[str, str]] = []
        else:
            conversation = await conversations.get_owned(session, user, conversation_id)
            history = await conversations.recent_history(session, conversation.id)
        await conversations.append_message(session, conversation, role=ChatRole.USER, content=question)
        await session.commit()
        conv_id = conversation.id

    # [2] ảnh chụp lộ trình của chính người hỏi.
    async with session_factory() as session:
        snapshot = await load_snapshot(session, user)
        if snapshot is not None and snapshot.last_opened_task_id is None:
            pass  # chưa mở việc nào: bước suy "việc hiện tại" sẽ dùng việc làm được ngay đầu tiên và nói rõ giả định

    try:
        llm: ChatCompletionPort | None = make_llm()
    except RuntimeError:
        llm = None  # chưa cấu hình khóa LLM: luật và công cụ lộ trình vẫn chạy được

    result = await _decide(
        question,
        snapshot=snapshot,
        history=history,
        llm=llm,
        embedding=embedding,
        session_factory=session_factory,
        tracer=tracer,
        today=today,
        now=now,
    )
    result.conversation_id = conv_id
    result.new_conversation = new_conversation

    # [7] ghi câu trả lời; câu chưa trả lời được thì ghi cho HR bổ sung tài liệu (ẩn danh khi HR xem).
    async with session_factory() as session:
        conversation = await conversations.get_owned(session, user, conv_id)
        message = await conversations.append_message(
            session,
            conversation,
            role=ChatRole.ASSISTANT,
            content=result.message,
            response_type=result.response_type,
            payload=result.payload(),
        )
        await session.commit()
        result.message_id = message.id
    # Cả câu không có căn cứ: ghi NO_BASIS. Trả lời được một phần: ghi PARTIAL (mức thấp hơn, kèm phần đã trả lời) để HR thấy
    # quy định còn thiếu mà không bị báo thiếu tài liệu oan.
    gap_kind = (
        GapKind.NO_BASIS
        if result.response_type == "NO_BASIS"
        else GapKind.PARTIAL
        if result.response_type == "ANSWER" and result.unanswered
        else None
    )
    if gap_kind is not None:
        try:
            async with session_factory() as session:
                await gaps.log_content_gap(
                    session,
                    user,
                    question,
                    kind=gap_kind,
                    answer_excerpt=result.message if gap_kind == GapKind.PARTIAL else None,
                )
        except Exception:
            logger.exception("viga_log_gap_failed")  # ghi số liệu phụ không được làm hỏng câu trả lời
    logger.info("viga_ask route=%s type=%s", result.route, result.response_type)  # không ghi nội dung (INV8)
    return result
