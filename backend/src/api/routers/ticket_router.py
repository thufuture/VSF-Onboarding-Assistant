"""`/api/v1/portal/tickets` và `/api/v1/portal/content-gaps` — ticket gửi HR và câu hỏi Viga chưa trả lời được (mục 17.5).

Nhân viên tạo ticket (sau khi xem và sửa) và xem ticket của chính mình; HR thấy ticket của phòng ban mình, nhận xử lý, trả lời,
đổi trạng thái; ADMIN thấy tất cả. Câu hỏi chưa trả lời được hiện **ẩn danh** cho HR của đúng phòng ban.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import (
    get_current_user,
    get_db,
    get_embedding_port,
    get_langfuse_tracer,
    get_optional_chat_completion_port,
    get_session_factory,
    get_storage_port,
    require_role,
)
from src.config import Settings, get_settings
from src.dto.request.viga_request_dto import (
    AddTicketMessageRequestDTO,
    CreateTicketRequestDTO,
    SetTicketStatusRequestDTO,
    SupplementGapRequestDTO,
)
from src.dto.response.viga_response_dto import (
    ContentGapResponseDTO,
    DissatisfiedGroupResponseDTO,
    RecheckGapResponseDTO,
    SatisfactionSummaryResponseDTO,
    SupplementGapResponseDTO,
    TicketDetailResponseDTO,
    TicketMessageResponseDTO,
    TicketSummaryResponseDTO,
)
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.model.enums import TicketStatus, UserRole
from src.model.user import User
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.ingest_service import today_in
from src.services.ingest.storage import StoragePort
from src.services.portal import ticket_service
from src.services.portal.errors import PortalError
from src.services.viga import feedback, gaps, supplement

router = APIRouter(prefix="/api/v1/portal", tags=["tickets"])

StaffUser = Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))]
CurrentUser = Annotated[User, Depends(get_current_user)]
Db = Annotated[AsyncSession, Depends(get_db)]


def _summary_dto(summary: ticket_service.TicketSummary) -> TicketSummaryResponseDTO:
    return TicketSummaryResponseDTO(**vars(summary))


def _detail_dto(detail: ticket_service.TicketDetail) -> TicketDetailResponseDTO:
    return TicketDetailResponseDTO(
        ticket=_summary_dto(detail.summary),
        messages=[TicketMessageResponseDTO(**vars(m)) for m in detail.messages],
    )


@router.post("/tickets", response_model=TicketSummaryResponseDTO, status_code=201)
async def create_ticket(
    body: CreateTicketRequestDTO, user: CurrentUser, db: Db, settings: Annotated[Settings, Depends(get_settings)]
) -> TicketSummaryResponseDTO:
    """Gửi câu hỏi cho HR phòng ban của người gửi. Tối đa 5 ticket/người/ngày; câu giống nhau trong 10 phút bị chặn."""
    ticket = await ticket_service.create_ticket(
        db,
        user,
        question=body.question,
        note=body.note,
        employee_task_id=body.employee_task_id,
        conversation_id=body.conversation_id,
        timezone=settings.app_timezone,
    )
    return _summary_dto((await ticket_service.get_ticket_detail(db, user, ticket.id)).summary)


@router.get("/tickets/mine")
async def list_my_tickets(user: CurrentUser, db: Db) -> list[TicketSummaryResponseDTO]:
    return [_summary_dto(s) for s in await ticket_service.list_my_tickets(db, user)]


@router.get("/tickets")
async def list_staff_tickets(
    user: StaffUser, db: Db, status: Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"] | None = None
) -> list[TicketSummaryResponseDTO]:
    return [_summary_dto(s) for s in await ticket_service.list_staff_tickets(db, user, status=status)]


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponseDTO)
async def get_ticket(ticket_id: int, user: CurrentUser, db: Db) -> TicketDetailResponseDTO:
    return _detail_dto(await ticket_service.get_ticket_detail(db, user, ticket_id))


@router.post("/tickets/{ticket_id}/messages", response_model=TicketDetailResponseDTO, status_code=201)
async def add_ticket_message(
    ticket_id: int, body: AddTicketMessageRequestDTO, user: CurrentUser, db: Db
) -> TicketDetailResponseDTO:
    await ticket_service.add_message(db, user, ticket_id, body.body)
    return _detail_dto(await ticket_service.get_ticket_detail(db, user, ticket_id))


@router.post("/tickets/{ticket_id}/claim", response_model=TicketDetailResponseDTO)
async def claim_ticket(ticket_id: int, user: StaffUser, db: Db) -> TicketDetailResponseDTO:
    await ticket_service.claim_ticket(db, user, ticket_id)
    return _detail_dto(await ticket_service.get_ticket_detail(db, user, ticket_id))


@router.patch("/tickets/{ticket_id}/status", response_model=TicketDetailResponseDTO)
async def set_ticket_status(
    ticket_id: int, body: SetTicketStatusRequestDTO, user: StaffUser, db: Db
) -> TicketDetailResponseDTO:
    await ticket_service.set_status(db, user, ticket_id, TicketStatus(body.status), body.resolution_note)
    return _detail_dto(await ticket_service.get_ticket_detail(db, user, ticket_id))


@router.get("/content-gaps")
async def list_content_gaps(user: StaffUser, db: Db, include_resolved: bool = False) -> list[ContentGapResponseDTO]:
    team_id = None if user.role == UserRole.ADMIN else await gaps.team_of(db, user.id)
    if user.role != UserRole.ADMIN and team_id is None:
        return []
    groups = await gaps.list_gap_groups(db, team_id=team_id, include_resolved=include_resolved)
    return [ContentGapResponseDTO(**vars(group)) for group in groups]


@router.post("/content-gaps/{gap_id}/resolve", status_code=204)
async def resolve_content_gap(gap_id: int, user: StaffUser, db: Db) -> Response:
    team_id = None if user.role == UserRole.ADMIN else await gaps.team_of(db, user.id)
    await gaps.resolve_group(db, gap_id=gap_id, team_id=team_id)
    return Response(status_code=204)


async def _staff_team(user: User, db: AsyncSession) -> tuple[int | None, bool]:
    """(phòng ban cần lọc, có dữ liệu để xem không): ADMIN thấy tất cả; HR chưa có phòng ban thì không thấy gì."""
    if user.role == UserRole.ADMIN:
        return None, True
    team_id = await gaps.team_of(db, user.id)
    return team_id, team_id is not None


@router.post("/content-gaps/{gap_id}/recheck", response_model=RecheckGapResponseDTO)
async def recheck_content_gap(
    gap_id: int,
    user: StaffUser,
    db: Db,
    settings: Annotated[Settings, Depends(get_settings)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    embedding: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    llm: Annotated[ChatCompletionPort | None, Depends(get_optional_chat_completion_port)],
    tracer: Annotated[LangfuseTracer, Depends(get_langfuse_tracer)],
) -> RecheckGapResponseDTO:
    """Hỏi lại đúng câu hỏi sau khi bổ sung tài liệu; trả lời được thì tự đánh dấu đã xử lý, chưa thì để mở."""
    if llm is None:
        raise PortalError(503, "LLM_NOT_CONFIGURED", "portal.llm_not_configured")
    team_id = None if user.role == UserRole.ADMIN else await gaps.team_of(db, user.id)
    today = datetime.now(ZoneInfo(settings.app_timezone)).date()
    result = await gaps.recheck_group(
        db,
        gap_id=gap_id,
        team_id=team_id,
        session_factory=session_factory,
        llm=llm,
        embedding=embedding,
        tracer=tracer,
        today=today,
    )
    return RecheckGapResponseDTO(**vars(result))


@router.get("/viga-feedback")
async def list_viga_feedback(
    user: StaffUser, db: Db, include_resolved: bool = False
) -> list[DissatisfiedGroupResponseDTO]:
    """Câu hỏi nhân viên bấm 👎, ẩn danh, gom theo câu hỏi."""
    team_id, visible = await _staff_team(user, db)
    if not visible:
        return []
    groups = await feedback.list_dissatisfied(db, team_id=team_id, include_resolved=include_resolved)
    return [DissatisfiedGroupResponseDTO(**vars(group)) for group in groups]


@router.get("/viga-feedback/summary", response_model=SatisfactionSummaryResponseDTO)
async def viga_feedback_summary(user: StaffUser, db: Db) -> SatisfactionSummaryResponseDTO:
    team_id, visible = await _staff_team(user, db)
    if not visible:
        return SatisfactionSummaryResponseDTO(up=0, down=0, open_down=0, satisfaction_percent=None)
    summary = await feedback.satisfaction_summary(db, team_id=team_id)
    return SatisfactionSummaryResponseDTO(
        up=summary.up,
        down=summary.down,
        open_down=summary.open_down,
        satisfaction_percent=summary.satisfaction_percent,
    )


@router.post("/viga-feedback/{feedback_id}/resolve", status_code=204)
async def resolve_viga_feedback(feedback_id: int, user: StaffUser, db: Db) -> Response:
    team_id = None if user.role == UserRole.ADMIN else await gaps.team_of(db, user.id)
    await feedback.resolve_dissatisfied(db, feedback_id=feedback_id, team_id=team_id)
    return Response(status_code=204)


@router.post("/content-gaps/{gap_id}/supplement", response_model=SupplementGapResponseDTO, status_code=202)
async def supplement_content_gap(
    gap_id: int,
    body: SupplementGapRequestDTO,
    user: StaffUser,
    db: Db,
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[StoragePort, Depends(get_storage_port)],
) -> SupplementGapResponseDTO:
    """HR viết câu trả lời đúng: thêm vào tài liệu "Hỏi đáp bổ sung" của phòng ban và xếp việc nền kích hoạt.

    Sau khi việc nền xong, giao diện gọi `recheck` để hỏi lại Viga; chỉ khi trả lời được câu mới tự đóng.
    """
    team_id = None if user.role == UserRole.ADMIN else await gaps.team_of(db, user.id)
    gap = await gaps.scoped_gap(db, gap_id, team_id)
    result = await supplement.add_answer(
        db,
        user=user,
        team_id=gap.team_id,
        question=body.question or gap.question_text,
        answer=body.answer,
        contact=body.contact,
        storage=storage,
        today=today_in(settings.app_timezone),
    )
    return SupplementGapResponseDTO(
        document_id=result.document_id,
        document_version_id=result.version_id,
        version_label=result.version_label,
        job_id=result.job_id,
    )
