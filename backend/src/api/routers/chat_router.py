"""`POST /api/v1/chat/ask` — viết lại câu hỏi, tìm kiếm hybrid song song cho từng câu hỏi con, sinh và
kiểm `claims[]` (2-D mở rộng). Yêu cầu đã đăng nhập (Phase 4).

Kế hoạch: docs/chatbot-vsf/plan/phase-2/2-c-2-d-tim-kiem-va-tra-loi-ke-hoach-chi-tiet.md
"""

from __future__ import annotations

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
    get_keep_warm,
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
from src.model.enums import DocumentStatus, UserRole, VersionStatus
from src.model.user import User
from src.services.auth.errors import AuthError
from src.services.ingest.embedding.keep_warm import KeepWarm
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.viga.answer_service import Claim
from src.services.viga.chat_throttle import ChatThrottle
from src.services.viga.pipeline import run_document_qa

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


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
    keep_warm: Annotated[KeepWarm | None, Depends(get_keep_warm)],
) -> ChatAskResponseDTO:
    # Endpoint tốn tiền thật (LLM + embedding) mỗi lần gọi — chặn lạm dụng/vòng lặp lỗi trước khi làm gì khác.
    wait = throttle.retry_after(user.id)
    if wait > 0:
        raise AuthError(429, "TOO_MANY_QUESTIONS", "chat.too_many_questions", headers={"Retry-After": str(wait)})
    throttle.record_question(user.id)
    if keep_warm is not None:
        keep_warm.touch()

    as_of = body.as_of or _today(settings.app_timezone)
    result = await run_document_qa(
        body.question,
        llm=llm,
        embedding=embedding,
        session_factory=session_factory,
        tracer=tracer,
        as_of=as_of,
    )
    return ChatAskResponseDTO(
        claims=[
            ClaimResponseDTO(
                question=claim.question,
                response_type=cast(Literal["ANSWER", "NO_BASIS"], claim.response_type),
                reason_code=claim.reason_code,
                text=claim.text,
                quote=claim.quote,
                source=_resolve_source(claim, result.section_by_chunk),
            )
            for claim in result.claims
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
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentContentResponseDTO:
    """Nội dung Markdown đầy đủ của một `document_version` — FE hiện trong modal, cuộn tới đúng section đã
    trích dẫn thay vì bắt người dùng tải file gốc rồi tự tìm (chỉ trả cho người đã đăng nhập, cùng mức truy
    cập với `/chat/ask` — không thêm kiểm tra `confidentiality` riêng vì người dùng đã nhận đúng section này
    làm nguồn trích dẫn từ một câu trả lời họ được phép thấy).
    """
    query = (
        select(DocumentVersion.markdown, DocumentVersion.version_label, Document.title)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(DocumentVersion.id == version_id)
    )
    if user.role == UserRole.USER:
        # Nhân viên chỉ đọc được bản đang áp dụng của tài liệu còn dùng: bản nháp chưa duyệt, bản đã thay thế và tài
        # liệu ngừng sử dụng không được lộ qua đường này.
        today = _today(settings.app_timezone)
        query = query.where(
            DocumentVersion.status == VersionStatus.ACTIVE,
            Document.status == DocumentStatus.ACTIVE,
            (DocumentVersion.effective_from.is_(None)) | (DocumentVersion.effective_from <= today),
            (DocumentVersion.effective_to.is_(None)) | (DocumentVersion.effective_to >= today),
        )
    row = (await session.execute(query)).one_or_none()
    if row is None:
        raise AuthError(404, "DOCUMENT_NOT_FOUND", "chat.document_not_found")
    markdown, version_label, title = row
    return DocumentContentResponseDTO(document_title=title, version_label=version_label, markdown=markdown)
