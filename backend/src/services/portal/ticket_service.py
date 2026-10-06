"""Ticket gửi HR (mục 17.5): nhân viên bấm "Gửi câu hỏi này cho HR" (hoặc tạo tay), HR của phòng ban nhận và trả lời.

Quy tắc đã chốt (quyết định 7, mục 0.1):
- Gửi tới **HR phòng ban** của nhân viên (hàng đợi chung của phòng ban; một HR bấm "Nhận xử lý" thì mới gán, tránh xử lý trùng).
- Nhân viên **xem và sửa** câu hỏi, thêm ghi chú trước khi gửi; Viga không tự tạo ticket.
- **5 ticket/người/ngày**; chặn câu giống nhau trong 10 phút.
- Đóng ticket **không** tự đổi trạng thái task liên quan (P0A D6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.chat_conversation import ChatConversation
from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import TicketSource, TicketStatus, UserRole
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.ticket import Ticket
from src.model.ticket_message import TicketMessage
from src.model.ticket_read import TicketRead
from src.model.user import User
from src.services.portal import ticket_attachment_service
from src.services.portal.errors import PortalError
from src.services.viga.guard import normalize_question

MAX_TICKETS_PER_DAY = 5
DUPLICATE_WINDOW = timedelta(minutes=10)
SUBJECT_MAX_CHARS = 120


@dataclass(frozen=True)
class TicketSummary:
    id: int
    subject: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime
    requester_name: str
    requester_email: str
    team_name: str
    assigned_hr_name: str | None
    related_task_title: str | None
    message_count: int
    last_sender_is_staff: bool  # tin cuối là của HR: nhân viên có phản hồi mới để xem
    resolution_note: str | None
    unread: bool = False  # có tin của phía bên kia mà người xem chưa mở


@dataclass(frozen=True)
class TicketMessageView:
    id: int
    sender_name: str
    sender_role: str
    body: str
    created_at: datetime
    mine: bool
    attachments: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class TicketDetail:
    summary: TicketSummary
    messages: list[TicketMessageView]


def _staff(user: User) -> bool:
    return user.role in (UserRole.HR, UserRole.ADMIN)


async def _team_ids(session: AsyncSession, user_id: int) -> list[int]:
    rows = await session.scalars(select(TeamMember.team_id).where(TeamMember.user_id == user_id))
    return [int(value) for value in rows.all()]


async def _first_team(session: AsyncSession, user_id: int) -> int | None:
    ids = sorted(await _team_ids(session, user_id))
    return ids[0] if ids else None


async def create_ticket(
    session: AsyncSession,
    user: User,
    *,
    question: str,
    note: str | None,
    employee_task_id: int | None,
    conversation_id: int | None,
    timezone: str,
    now: datetime | None = None,
    attachment_ids: list[int] | None = None,
) -> Ticket:
    now = now or datetime.now(UTC)
    text = " ".join(question.split())
    if not text:
        raise PortalError(422, "TICKET_QUESTION_REQUIRED", "portal.ticket_question_required")
    team_id = await _first_team(session, user.id)
    if team_id is None:
        raise PortalError(409, "NO_TEAM_ASSIGNED", "portal.no_team_assigned")

    local_midnight = datetime.now(ZoneInfo(timezone)).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await session.scalar(
        select(func.count(Ticket.id)).where(Ticket.created_by_user_id == user.id, Ticket.created_at >= local_midnight)
    )
    if int(today_count or 0) >= MAX_TICKETS_PER_DAY:
        raise PortalError(429, "TICKET_DAILY_LIMIT", "portal.ticket_daily_limit")

    wanted = normalize_question(text)
    recent = await session.scalars(
        select(Ticket.subject).where(Ticket.created_by_user_id == user.id, Ticket.created_at >= now - DUPLICATE_WINDOW)
    )
    if any(normalize_question(subject) == wanted for subject in recent.all()):
        raise PortalError(409, "TICKET_DUPLICATE", "portal.ticket_duplicate")

    # Chỉ nhận việc và cuộc trò chuyện thuộc chính người gửi; mã lạ bị bỏ qua thay vì lộ việc của người khác.
    related_task_id: int | None = None
    if employee_task_id is not None:
        owned = await session.scalar(
            select(EmployeeTask.id)
            .join(EmployeeJourney, EmployeeJourney.id == EmployeeTask.employee_journey_id)
            .where(EmployeeTask.id == employee_task_id, EmployeeJourney.user_id == user.id)
        )
        related_task_id = int(owned) if owned is not None else None
    valid_conversation: int | None = None
    if conversation_id is not None:
        conversation = await session.get(ChatConversation, conversation_id)
        valid_conversation = conversation.id if conversation is not None and conversation.user_id == user.id else None

    ticket = Ticket(
        team_id=team_id,
        created_by_user_id=user.id,
        related_employee_task_id=related_task_id,
        subject=text[:SUBJECT_MAX_CHARS],
        source=TicketSource.VIGA.value if valid_conversation is not None else TicketSource.MANUAL.value,
        conversation_id=valid_conversation,
    )
    session.add(ticket)
    await session.flush()
    body = text if not note or not note.strip() else f"{text}\n\nGhi chú của nhân viên: {note.strip()}"
    first = TicketMessage(ticket_id=ticket.id, sender_user_id=user.id, body=body)
    session.add(first)
    await session.flush()
    await ticket_attachment_service.link(session, user, attachment_ids or [], first.id)
    await session.commit()
    return ticket


async def _load_for_user(session: AsyncSession, user: User, ticket_id: int) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None or ticket.deleted_at is not None:
        raise PortalError(404, "TICKET_NOT_FOUND", "portal.ticket_not_found")
    if ticket.created_by_user_id == user.id or user.role == UserRole.ADMIN:
        return ticket
    if user.role == UserRole.HR and ticket.team_id in await _team_ids(session, user.id):
        return ticket
    # Không phân biệt "không có" với "không phải của bạn" để không lộ sự tồn tại của ticket người khác.
    raise PortalError(404, "TICKET_NOT_FOUND", "portal.ticket_not_found")


async def unread_ticket_ids(session: AsyncSession, user: User, ticket_ids: list[int] | None = None) -> set[int]:
    """Mã các ticket có tin của PHÍA BÊN KIA mới hơn mốc đã xem của `user`.

    Nhân viên: tin của HR/Admin. HR và Admin: tin của nhân viên (HR đồng nghiệp trả lời không làm ticket "chưa đọc").
    Không truyền `ticket_ids` thì xét mọi ticket mà `user` được thấy.
    """
    staff = _staff(user)
    latest = (
        select(TicketMessage.ticket_id.label("ticket_id"), func.max(TicketMessage.id).label("last_id"))
        .join(User, User.id == TicketMessage.sender_user_id)
        .where(User.role == UserRole.USER if staff else User.role != UserRole.USER)
        .group_by(TicketMessage.ticket_id)
        .subquery()
    )
    query = (
        select(Ticket.id)
        .join(latest, latest.c.ticket_id == Ticket.id)
        .outerjoin(TicketRead, (TicketRead.ticket_id == Ticket.id) & (TicketRead.user_id == user.id))
        .where(Ticket.deleted_at.is_(None), latest.c.last_id > func.coalesce(TicketRead.last_read_message_id, 0))
    )
    if ticket_ids is not None:
        query = query.where(Ticket.id.in_(ticket_ids))
    elif user.role == UserRole.ADMIN:
        pass
    elif user.role == UserRole.HR:
        query = query.where(Ticket.team_id.in_(await _team_ids(session, user.id)))
    else:
        query = query.where(Ticket.created_by_user_id == user.id)
    return {int(value) for value in (await session.scalars(query)).all()}


async def mark_read(session: AsyncSession, user: User, ticket_id: int) -> None:
    """Người xem đã mở ticket: đánh dấu đã xem tới tin cuối cùng hiện có."""
    ticket = await _load_for_user(session, user, ticket_id)
    last = await session.scalar(select(func.max(TicketMessage.id)).where(TicketMessage.ticket_id == ticket.id))
    statement = pg_insert(TicketRead).values(ticket_id=ticket.id, user_id=user.id, last_read_message_id=int(last or 0))
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[TicketRead.ticket_id, TicketRead.user_id],
            set_={"last_read_message_id": statement.excluded.last_read_message_id, "updated_at": func.now()},
        )
    )
    await session.commit()


async def _summaries(session: AsyncSession, tickets: list[Ticket], viewer: User | None = None) -> list[TicketSummary]:
    if not tickets:
        return []
    unread = await unread_ticket_ids(session, viewer, [t.id for t in tickets]) if viewer is not None else set()
    ids = [t.id for t in tickets]
    user_ids = {t.created_by_user_id for t in tickets} | {t.assigned_hr_id for t in tickets if t.assigned_hr_id}
    user_rows = (
        await session.execute(select(User.id, User.display_name, User.email).where(User.id.in_(user_ids)))
    ).all()
    names = {uid: name for uid, name, _ in user_rows}
    emails = {uid: email for uid, _, email in user_rows}
    team_names = {
        tid: name
        for tid, name in (
            await session.execute(select(Team.id, Team.name).where(Team.id.in_({t.team_id for t in tickets})))
        ).all()
    }
    task_ids = {t.related_employee_task_id for t in tickets if t.related_employee_task_id}
    task_titles: dict[int, str] = {}
    if task_ids:
        rows = await session.execute(select(EmployeeTask.id, EmployeeTask.title).where(EmployeeTask.id.in_(task_ids)))
        task_titles = {tid: title for tid, title in rows.all()}
    counts = {
        tid: count
        for tid, count in (
            await session.execute(
                select(TicketMessage.ticket_id, func.count())
                .where(TicketMessage.ticket_id.in_(ids))
                .group_by(TicketMessage.ticket_id)
            )
        ).all()
    }
    last_sender: dict[int, int] = {}
    last_rows = await session.execute(
        select(TicketMessage.ticket_id, TicketMessage.sender_user_id)
        .where(TicketMessage.ticket_id.in_(ids))
        .order_by(TicketMessage.id)
    )
    for ticket_id, sender in last_rows.all():  # dòng cuối ghi đè dòng trước: còn lại tin cuối cùng
        last_sender[ticket_id] = sender
    staff_ids = set(
        (
            await session.scalars(
                select(User.id).where(
                    User.id.in_(set(last_sender.values())), User.role.in_([UserRole.HR, UserRole.ADMIN])
                )
            )
        ).all()
    )
    return [
        TicketSummary(
            id=t.id,
            subject=t.subject,
            status=t.status,
            source=t.source,
            created_at=t.created_at,
            updated_at=t.updated_at,
            requester_name=names.get(t.created_by_user_id, ""),
            requester_email=emails.get(t.created_by_user_id, ""),
            team_name=team_names.get(t.team_id, ""),
            assigned_hr_name=names.get(t.assigned_hr_id) if t.assigned_hr_id else None,
            related_task_title=task_titles.get(t.related_employee_task_id) if t.related_employee_task_id else None,
            message_count=counts.get(t.id, 0),
            last_sender_is_staff=last_sender.get(t.id) in staff_ids,
            resolution_note=t.resolution_note,
            unread=t.id in unread,
        )
        for t in tickets
    ]


async def list_my_tickets(session: AsyncSession, user: User) -> list[TicketSummary]:
    tickets = (
        await session.scalars(
            select(Ticket)
            .where(Ticket.created_by_user_id == user.id, Ticket.deleted_at.is_(None))
            .order_by(Ticket.updated_at.desc(), Ticket.id.desc())
        )
    ).all()
    return await _summaries(session, list(tickets), user)


async def list_staff_tickets(session: AsyncSession, user: User, *, status: str | None = None) -> list[TicketSummary]:
    """Ticket trong phạm vi HR (các phòng ban của HR); ADMIN thấy tất cả."""
    query = select(Ticket).where(Ticket.deleted_at.is_(None)).order_by(Ticket.updated_at.desc(), Ticket.id.desc())
    if user.role != UserRole.ADMIN:
        query = query.where(Ticket.team_id.in_(await _team_ids(session, user.id)))
    if status is not None:
        query = query.where(Ticket.status == status)
    return await _summaries(session, list((await session.scalars(query)).all()), user)


async def get_ticket_detail(session: AsyncSession, user: User, ticket_id: int) -> TicketDetail:
    ticket = await _load_for_user(session, user, ticket_id)
    summary = (await _summaries(session, [ticket], user))[0]
    rows = await session.execute(
        select(TicketMessage, User.display_name, User.role)
        .join(User, User.id == TicketMessage.sender_user_id)
        .where(TicketMessage.ticket_id == ticket.id)
        .order_by(TicketMessage.id)
    )
    found = rows.all()
    attached = await ticket_attachment_service.by_message(session, [m.id for m, _, _ in found])
    messages = [
        TicketMessageView(m.id, name, role, m.body, m.created_at, m.sender_user_id == user.id, attached.get(m.id, []))
        for m, name, role in found
    ]
    return TicketDetail(summary, messages)


async def add_message(
    session: AsyncSession, user: User, ticket_id: int, body: str, attachment_ids: list[int] | None = None
) -> None:
    ticket = await _load_for_user(session, user, ticket_id)
    text = body.strip()
    if not text:
        raise PortalError(422, "TICKET_MESSAGE_REQUIRED", "portal.ticket_message_required")
    if ticket.status == TicketStatus.CLOSED:
        raise PortalError(409, "TICKET_CLOSED", "portal.ticket_closed")
    message = TicketMessage(ticket_id=ticket.id, sender_user_id=user.id, body=text)
    session.add(message)
    await session.flush()
    await ticket_attachment_service.link(session, user, attachment_ids or [], message.id)
    ticket.updated_at = func.now()
    if _staff(user):
        if ticket.assigned_hr_id is None:
            ticket.assigned_hr_id = user.id  # HR đầu tiên trả lời coi như nhận xử lý
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS.value
    await session.commit()


async def claim_ticket(session: AsyncSession, user: User, ticket_id: int) -> None:
    ticket = await _load_for_user(session, user, ticket_id)
    if not _staff(user):
        raise PortalError(403, "FORBIDDEN_ROLE", "auth.forbidden_role")
    if ticket.assigned_hr_id not in (None, user.id):
        raise PortalError(409, "TICKET_ALREADY_CLAIMED", "portal.ticket_already_claimed")
    ticket.assigned_hr_id = user.id
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS.value
    await session.commit()


async def set_status(
    session: AsyncSession, user: User, ticket_id: int, status: TicketStatus, resolution_note: str | None
) -> None:
    ticket = await _load_for_user(session, user, ticket_id)
    if not _staff(user):
        raise PortalError(403, "FORBIDDEN_ROLE", "auth.forbidden_role")
    ticket.status = status.value
    if resolution_note is not None:
        ticket.resolution_note = resolution_note.strip() or None
    await session.commit()
