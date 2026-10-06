"""`/api/v1/viga` — Viga của nhân viên: hỏi (công cụ lộ trình hoặc tài liệu), hội thoại kiểu ChatGPT (mục 6.2, 15, 17).

Giao diện chỉ gửi câu hỏi và `conversation_id`. Mọi công cụ chỉ đọc lộ trình của CHÍNH người đăng nhập (`user_id` lấy từ
phiên). Hội thoại chỉ chủ sở hữu đọc được; không gửi nội dung sang Langfuse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, cast
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import (
    get_chat_throttle,
    get_current_user,
    get_db,
    get_embedding_port,
    get_keep_warm,
    get_langfuse_tracer,
    get_optional_chat_completion_port,
    get_session_factory,
)
from src.config import Settings, get_settings
from src.dto.request.viga_request_dto import RenameConversationRequestDTO, VigaAskRequestDTO, VigaFeedbackRequestDTO
from src.dto.response.error_response_dto import ErrorResponseDTO
from src.dto.response.viga_response_dto import (
    ConversationDetailResponseDTO,
    ConversationMessageResponseDTO,
    ConversationResponseDTO,
    VigaActionResponseDTO,
    VigaAnswerResponseDTO,
    VigaBlockingTaskResponseDTO,
    VigaClaimResponseDTO,
    VigaFeedbackResponseDTO,
    VigaFeedbackSummaryResponseDTO,
    VigaSourceRefResponseDTO,
    VigaSourceResponseDTO,
)
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.model.enums import FeedbackRating, FeedbackReason
from src.model.user import User
from src.services.auth.errors import AuthError
from src.services.ingest.embedding.keep_warm import KeepWarm
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.viga import conversations, feedback
from src.services.viga.chat_throttle import ChatThrottle
from src.services.viga.service import VigaResult, ask_viga

router = APIRouter(prefix="/api/v1/viga", tags=["viga"])

_ERRORS: dict[int | str, dict[str, Any]] = {401: {"model": ErrorResponseDTO}, 404: {"model": ErrorResponseDTO}}


def _answer_dto(result: VigaResult) -> VigaAnswerResponseDTO:
    return VigaAnswerResponseDTO(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        new_conversation=result.new_conversation,
        response_type=cast(Literal["ANSWER"], result.response_type),
        message=result.message,
        message_key=result.message_key,
        message_params=result.message_params,
        claims=[
            VigaClaimResponseDTO(
                question=c.question,
                response_type=cast(Literal["ANSWER", "NO_BASIS"], c.response_type),
                text=c.text,
                quote=c.quote,
                source=VigaSourceResponseDTO(**vars(c.source)) if c.source else None,
            )
            for c in result.claims
        ],
        blocking_tasks=[
            VigaBlockingTaskResponseDTO(task_id=b.task_id, title=b.title, state=cast(Literal["done"], b.state))
            for b in result.blocking_tasks
        ],
        suggested_actions=[VigaActionResponseDTO(**vars(a)) for a in result.actions],
        sources=[VigaSourceRefResponseDTO(**vars(s)) for s in result.sources],
        can_report_to_hr=result.can_report,
        unanswered=result.unanswered,
        assumed_task_title=result.assumed_title,
        route=result.route,
    )


@router.post("/ask", response_model=VigaAnswerResponseDTO, responses={**_ERRORS, 429: {"model": ErrorResponseDTO}})
async def ask(
    body: VigaAskRequestDTO,
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    embedding: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    llm: Annotated[ChatCompletionPort | None, Depends(get_optional_chat_completion_port)],
    tracer: Annotated[LangfuseTracer, Depends(get_langfuse_tracer)],
    throttle: Annotated[ChatThrottle, Depends(get_chat_throttle)],
    keep_warm: Annotated[KeepWarm | None, Depends(get_keep_warm)],
) -> VigaAnswerResponseDTO:
    # Endpoint có thể tốn tiền thật (LLM, embedding): chặn lạm dụng bằng cùng bộ đếm với `/chat/ask`.
    wait = throttle.retry_after(user.id)
    if wait > 0:
        raise AuthError(429, "TOO_MANY_QUESTIONS", "chat.too_many_questions", headers={"Retry-After": str(wait)})
    throttle.record_question(user.id)
    if keep_warm is not None:
        keep_warm.touch()

    def make_llm() -> ChatCompletionPort:
        if llm is None:
            raise RuntimeError("LLM_API_KEY chưa cấu hình")
        return llm

    today = body.as_of or datetime.now(ZoneInfo(settings.app_timezone)).date()
    with tracer.span(
        "viga.ask",
        input=body.question,
        user_id=user.id,
        session_id=f"viga-{body.conversation_id}" if body.conversation_id else None,
        tags=["viga", user.role.value if hasattr(user.role, "value") else str(user.role)],
    ) as root:
        result = await ask_viga(
            user=user,
            question=body.question,
            conversation_id=body.conversation_id,
            session_factory=session_factory,
            embedding=embedding,
            make_llm=make_llm,
            tracer=tracer,
            today=today,
        )
        root.update(
            output={"response_type": result.response_type, "route": result.route, "message": result.message},
            metadata={"conversation_id": result.conversation_id, "message_id": result.message_id},
        )
    return _answer_dto(result)


@router.get("/conversations")
async def list_conversations(
    user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]
) -> list[ConversationResponseDTO]:
    rows = await conversations.list_conversations(db, user)
    return [ConversationResponseDTO.model_validate(row, from_attributes=True) for row in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponseDTO, responses=_ERRORS)
async def get_conversation(
    conversation_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationDetailResponseDTO:
    conversation = await conversations.get_owned(db, user, conversation_id)
    messages = await conversations.list_messages(db, conversation)
    ratings = await feedback.feedback_by_message(db, [m.id for m in messages])
    items: list[ConversationMessageResponseDTO] = []
    for message in messages:
        item = ConversationMessageResponseDTO.model_validate(message, from_attributes=True)
        rated = ratings.get(message.id)
        if rated is not None:
            item.feedback = VigaFeedbackSummaryResponseDTO(
                rating=cast(Literal["UP"], rated.rating), reason=rated.reason
            )
        items.append(item)
    return ConversationDetailResponseDTO(
        conversation=ConversationResponseDTO.model_validate(conversation, from_attributes=True), messages=items
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponseDTO, responses=_ERRORS)
async def rename_conversation(
    conversation_id: int,
    body: RenameConversationRequestDTO,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationResponseDTO:
    conversation = await conversations.get_owned(db, user, conversation_id)
    renamed = await conversations.rename(db, conversation, body.title)
    return ConversationResponseDTO.model_validate(renamed, from_attributes=True)


@router.delete("/conversations/{conversation_id}", status_code=204, responses=_ERRORS)
async def delete_conversation(
    conversation_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    conversation = await conversations.get_owned(db, user, conversation_id)
    await conversations.delete_conversation(db, conversation)
    return Response(status_code=204)


@router.put("/messages/{message_id}/feedback", response_model=VigaFeedbackResponseDTO, responses=_ERRORS)
async def rate_answer(
    message_id: int,
    body: VigaFeedbackRequestDTO,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VigaFeedbackResponseDTO:
    """👍/👎 cho một câu trả lời của Viga (bấm lại để đổi). Chỉ chủ hội thoại đánh giá được."""
    saved = await feedback.set_feedback(
        db,
        user,
        message_id,
        rating=FeedbackRating(body.rating),
        reason=FeedbackReason(body.reason) if body.reason else None,
        comment=body.comment,
    )
    return VigaFeedbackResponseDTO(
        message_id=saved.message_id,
        rating=cast(Literal["UP"], saved.rating),
        reason=saved.reason,
        comment=saved.comment,
    )


@router.delete("/messages/{message_id}/feedback", status_code=204, responses=_ERRORS)
async def clear_rating(
    message_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await feedback.clear_feedback(db, user, message_id)
    return Response(status_code=204)
