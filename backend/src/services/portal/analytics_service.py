"""Số liệu cho trang Tổng quan của HR và Admin: tiến độ nhân viên, tài liệu, Viga, ticket, chi phí và độ trễ AI.

Phạm vi: **HR chỉ thấy phòng ban của mình** (nhân viên, task, ticket, câu hỏi chưa trả lời được, và chi phí/độ trễ AI của chính những
người trong phòng ban); **Admin thấy tất cả**. Tài liệu dùng chung một kho nên số liệu tài liệu không lọc theo phòng ban.

Chỉ trả số liệu tổng hợp: không có nội dung câu hỏi, câu trả lời hay tài liệu, và không lộ câu hỏi của từng người (INV8).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dto.response.analytics_response_dto import (
    AiAnalyticsResponseDTO,
    CostGroupResponseDTO,
    DocumentAnalyticsResponseDTO,
    GroupTaskStateResponseDTO,
    JobRunResponseDTO,
    LabelCountResponseDTO,
    OperationBreakdownResponseDTO,
    PeopleAnalyticsResponseDTO,
    PortalAnalyticsResponseDTO,
    ProviderBreakdownResponseDTO,
    TicketAnalyticsResponseDTO,
    VigaAnalyticsResponseDTO,
)
from src.model.chat_conversation import ChatConversation
from src.model.chat_message import ChatMessage
from src.model.content_gap import ContentGap
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_version import DocumentVersion
from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import ChatRole, DocumentStatus, EmployeeTaskStatus, JobKind, JobStatus, TicketStatus, UserRole
from src.model.job import Job
from src.model.llm_call import LlmCall
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.ticket import Ticket
from src.model.ticket_message import TicketMessage
from src.model.user import User
from src.services.ingest.version_lifecycle import display_state

RUN_LIMIT = 20
TOP_CATEGORIES = 8
PROGRESS_KEYS = ("NO_JOURNEY", "NOT_STARTED", "IN_PROGRESS", "COMPLETED")
VERSION_STATES = ("CURRENT", "SCHEDULED", "DRAFT", "PROCESSING", "SUPERSEDED", "FAILED")
TASK_GROUPS = ("PROFILE", "TRAINING", "DEVICE", "OFFICE", "NONE")
ROUTES = ("SHORTCUT", "GUARD", "LLM", "FALLBACK")
UNANSWERED = {"NO_BASIS", "OUT_OF_SCOPE", "ERROR"}
NO_LLM_ROUTES = {"SHORTCUT", "GUARD"}


def _local_day(column: Any, timezone: str) -> Any:
    """Cột thời gian đổi sang NGÀY theo múi giờ ứng dụng (ngày Việt Nam, không phải ngày UTC)."""
    return cast(func.timezone(timezone, column), Date)


def _per_day(rows: Sequence[Any], dates: list[date], *, as_float: bool = False) -> list[Any]:
    by_day = {day: value for day, value in rows}
    return [float(by_day.get(day, 0.0)) if as_float else int(by_day.get(day, 0)) for day in dates]


def _labels(counter: Counter[str] | dict[str, int], order: Sequence[str]) -> list[LabelCountResponseDTO]:
    """Danh sách nhãn theo thứ tự cố định, luôn đủ khóa (khóa vắng thì 0) để biểu đồ không đổi hình theo dữ liệu."""
    known = [LabelCountResponseDTO(key=key, count=int(counter.get(key, 0))) for key in order]
    extra = [LabelCountResponseDTO(key=key, count=int(n)) for key, n in counter.items() if key not in order]
    return known + sorted(extra, key=lambda item: -item.count)


async def _scope_team(session: AsyncSession, user: User) -> tuple[int | None, str | None]:
    if user.role == UserRole.ADMIN:
        return None, None
    team_id = await session.scalar(
        select(TeamMember.team_id).where(TeamMember.user_id == user.id).order_by(TeamMember.team_id).limit(1)
    )
    if team_id is None:
        return None, None
    return int(team_id), await session.scalar(select(Team.name).where(Team.id == team_id))


async def _people(
    session: AsyncSession, *, team_id: int | None, admin: bool, dates: list[date], start: datetime, timezone: str
) -> PeopleAnalyticsResponseDTO:
    employees = select(User.id).where(User.role == UserRole.USER)
    if not admin:
        employees = employees.where(User.id.in_(select(TeamMember.user_id).where(TeamMember.team_id == team_id)))
    employee_ids = [int(value) for value in (await session.scalars(employees)).all()]

    latest: dict[int, int] = {}  # user_id -> journey_id mới nhất
    if employee_ids:
        rows = await session.execute(
            select(EmployeeJourney.user_id, func.max(EmployeeJourney.id))
            .where(EmployeeJourney.user_id.in_(employee_ids), EmployeeJourney.deleted_at.is_(None))
            .group_by(EmployeeJourney.user_id)
        )
        latest = {int(user_id): int(journey_id) for user_id, journey_id in rows.all()}

    state_counter: Counter[str] = Counter()
    group_counter: dict[str, Counter[str]] = defaultdict(Counter)
    per_journey: dict[int, list[int]] = defaultdict(lambda: [0, 0])  # journey -> [tổng, xong]
    if latest:
        rows = await session.execute(
            select(EmployeeTask.employee_journey_id, EmployeeTask.status, EmployeeTask.task_group, func.count())
            .where(EmployeeTask.employee_journey_id.in_(list(latest.values())), EmployeeTask.deleted_at.is_(None))
            .group_by(EmployeeTask.employee_journey_id, EmployeeTask.status, EmployeeTask.task_group)
        )
        for journey_id, status, group, count in rows.all():
            state = (
                "done"
                if status == EmployeeTaskStatus.DONE
                else "ready"
                if status == EmployeeTaskStatus.READY
                else "locked"
            )
            state_counter[state] += int(count)
            group_counter[group or "NONE"][state] += int(count)
            per_journey[int(journey_id)][0] += int(count)
            if state == "done":
                per_journey[int(journey_id)][1] += int(count)

    progress: Counter[str] = Counter()
    for user_id in employee_ids:
        journey_id = latest.get(user_id)
        total, done = per_journey[journey_id] if journey_id is not None else (0, 0)
        if journey_id is None:
            progress["NO_JOURNEY"] += 1
        elif total > 0 and done == total:
            progress["COMPLETED"] += 1
        elif done > 0:
            progress["IN_PROGRESS"] += 1
        else:
            progress["NOT_STARTED"] += 1

    completed_rows: Sequence[tuple[date, int]] = []
    if latest:
        day = _local_day(EmployeeTask.completed_at, timezone)
        completed_rows = (
            await session.execute(
                select(day, func.count())
                .where(
                    EmployeeTask.employee_journey_id.in_(list(latest.values())),
                    EmployeeTask.completed_at.is_not(None),
                    EmployeeTask.completed_at >= start,
                )
                .group_by(day)
            )
        ).all()  # type: ignore[assignment]

    total_tasks = sum(state_counter.values())
    return PeopleAnalyticsResponseDTO(
        employees_total=len(employee_ids),
        completion_percent=round(100 * state_counter["done"] / total_tasks) if total_tasks else 0,
        by_progress=_labels(progress, PROGRESS_KEYS),
        tasks_by_state=_labels(state_counter, ("done", "ready", "locked")),
        tasks_by_group=[
            GroupTaskStateResponseDTO(
                group=group,
                done=group_counter[group]["done"],
                ready=group_counter[group]["ready"],
                locked=group_counter[group]["locked"],
            )
            for group in TASK_GROUPS
            if group in group_counter
        ],
        completed_per_day=_per_day(completed_rows, dates),
    )


async def _documents(session: AsyncSession, today: date) -> DocumentAnalyticsResponseDTO:
    total = await session.scalar(select(func.count(Document.id)).where(Document.status == DocumentStatus.ACTIVE))
    rows = await session.execute(
        select(DocumentVersion.status, DocumentVersion.effective_from, DocumentVersion.effective_to)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(Document.status == DocumentStatus.ACTIVE)
    )
    states: Counter[str] = Counter(display_state(status, start, end, today) for status, start, end in rows.all())
    categories = await session.execute(
        select(DocumentCategory.name, func.count(Document.id))
        .join(Document, Document.category_id == DocumentCategory.id)
        .where(Document.status == DocumentStatus.ACTIVE)
        .group_by(DocumentCategory.name)
        .order_by(func.count(Document.id).desc(), DocumentCategory.name)
        .limit(TOP_CATEGORIES)
    )
    return DocumentAnalyticsResponseDTO(
        total=int(total or 0),
        by_state=_labels(states, VERSION_STATES),
        by_category=[LabelCountResponseDTO(key=name, count=int(count)) for name, count in categories.all()],
    )


async def _viga(
    session: AsyncSession, *, scoped_users: list[int] | None, dates: list[date], start: datetime, timezone: str
) -> VigaAnalyticsResponseDTO:
    scope = [] if scoped_users is None else [ChatConversation.user_id.in_(scoped_users)]
    if scoped_users is not None and not scoped_users:
        return VigaAnalyticsResponseDTO(
            total_questions=0,
            questions_per_day=[0] * len(dates),
            by_outcome=_labels({}, ()),
            by_route=_labels({}, ROUTES),
            no_llm_percent=0,
            answered_percent=0,
        )
    day = _local_day(ChatMessage.created_at, timezone)
    questions = (
        await session.execute(
            select(day, func.count())
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(ChatMessage.role == ChatRole.USER, ChatMessage.created_at >= start, *scope)
            .group_by(day)
        )
    ).all()
    outcomes = (
        await session.execute(
            select(ChatMessage.response_type, func.count())
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(ChatMessage.role == ChatRole.ASSISTANT, ChatMessage.created_at >= start, *scope)
            .group_by(ChatMessage.response_type)
        )
    ).all()
    route_expr = ChatMessage.payload["route"].astext
    routes = (
        await session.execute(
            select(route_expr, func.count())
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(ChatMessage.role == ChatRole.ASSISTANT, ChatMessage.created_at >= start, *scope)
            .group_by(route_expr)
        )
    ).all()
    outcome_counter = Counter({(key or "INFO"): int(count) for key, count in outcomes})
    route_counter = Counter({key: int(count) for key, count in routes if key})
    answers = sum(outcome_counter.values())
    answered = sum(count for key, count in outcome_counter.items() if key not in UNANSWERED)
    no_llm = sum(count for key, count in route_counter.items() if key in NO_LLM_ROUTES)
    routed = sum(route_counter.values())
    return VigaAnalyticsResponseDTO(
        total_questions=sum(int(count) for _, count in questions),
        questions_per_day=_per_day(questions, dates),
        by_outcome=_labels(
            outcome_counter,
            (
                "ANSWER",
                "NEXT_STEP",
                "DAY_PLAN",
                "PREREQUISITE_REQUIRED",
                "INFO",
                "CLARIFY",
                "NO_BASIS",
                "OUT_OF_SCOPE",
                "ERROR",
            ),
        ),
        by_route=_labels(route_counter, ROUTES),
        no_llm_percent=round(100 * no_llm / routed) if routed else 0,
        answered_percent=round(100 * answered / answers) if answers else 0,
    )


async def _tickets(
    session: AsyncSession, *, team_id: int | None, admin: bool, dates: list[date], start: datetime, timezone: str
) -> TicketAnalyticsResponseDTO:
    if not admin and team_id is None:
        return TicketAnalyticsResponseDTO(
            by_status=_labels({}, [s.value for s in TicketStatus]),
            created_per_day=[0] * len(dates),
            open_gaps=0,
            avg_first_reply_hours=None,
        )
    scope = [] if admin else [Ticket.team_id == team_id]
    by_status = (
        await session.execute(
            select(Ticket.status, func.count()).where(Ticket.deleted_at.is_(None), *scope).group_by(Ticket.status)
        )
    ).all()
    day = _local_day(Ticket.created_at, timezone)
    created = (
        await session.execute(
            select(day, func.count())
            .where(Ticket.deleted_at.is_(None), Ticket.created_at >= start, *scope)
            .group_by(day)
        )
    ).all()
    first_reply = (
        select(TicketMessage.ticket_id, func.min(TicketMessage.created_at).label("replied_at"))
        .join(User, User.id == TicketMessage.sender_user_id)
        .where(User.role.in_([UserRole.HR, UserRole.ADMIN]))
        .group_by(TicketMessage.ticket_id)
        .subquery()
    )
    delays = (
        await session.execute(
            select(func.extract("epoch", first_reply.c.replied_at - Ticket.created_at))
            .join(first_reply, first_reply.c.ticket_id == Ticket.id)
            .where(Ticket.deleted_at.is_(None), Ticket.created_at >= start, *scope)
        )
    ).all()
    seconds = [float(value) for (value,) in delays if value is not None and value >= 0]
    gap_scope = [] if admin else [ContentGap.team_id == team_id]
    open_gaps = await session.scalar(
        select(func.count(ContentGap.id)).where(ContentGap.resolved_at.is_(None), *gap_scope)
    )
    return TicketAnalyticsResponseDTO(
        by_status=_labels({key: int(count) for key, count in by_status}, [s.value for s in TicketStatus]),
        created_per_day=_per_day(created, dates),
        open_gaps=int(open_gaps or 0),
        avg_first_reply_hours=round(sum(seconds) / len(seconds) / 3600, 1) if seconds else None,
    )


def _empty_ai(dates: list[date]) -> AiAnalyticsResponseDTO:
    return AiAnalyticsResponseDTO(
        calls=0,
        errors=0,
        cost_usd=0.0,
        calls_per_day=[0] * len(dates),
        errors_per_day=[0] * len(dates),
        cost_per_day=[0.0] * len(dates),
        by_operation=[],
        by_provider=[],
        cost_groups=[],
        hours=[],
        task_runs=[],
        activation_runs=[],
    )


async def _runs(
    session: AsyncSession, kind: JobKind, *, scoped_users: list[int] | None, start: datetime
) -> list[JobRunResponseDTO]:
    query = (
        select(Job)
        .where(
            Job.kind == kind.value,
            Job.status.in_([JobStatus.SUCCEEDED.value, JobStatus.FAILED.value]),
            Job.created_at >= start,
        )
        .order_by(Job.id.desc())
        .limit(RUN_LIMIT)
    )
    if scoped_users is not None:
        query = query.where(Job.created_by.in_(scoped_users))
    jobs = list((await session.scalars(query)).all())
    if not jobs:
        return []
    sums = {
        int(job_id): (int(calls), float(latency or 0), int(prompt or 0), int(completion or 0), float(cost or 0))
        for job_id, calls, latency, prompt, completion, cost in (
            await session.execute(
                select(
                    LlmCall.job_id,
                    func.count(),
                    func.sum(LlmCall.latency_ms),
                    func.sum(LlmCall.prompt_tokens),
                    func.sum(LlmCall.completion_tokens),
                    func.sum(LlmCall.cost_usd),
                )
                .where(LlmCall.job_id.in_([job.id for job in jobs]))
                .group_by(LlmCall.job_id)
            )
        ).all()
    }
    runs: list[JobRunResponseDTO] = []
    for job in reversed(jobs):  # cũ trước mới sau để vẽ theo thời gian
        result = job.result or {}
        if kind == JobKind.AI_TASK_PROPOSAL:
            documents = len(job.payload.get("version_ids", []))
            items = sum(len(entry.get("proposals", [])) for entry in result.get("documents", []))
        else:
            documents = 1
            items = int(result.get("chunk_count", 0))
        calls, latency, prompt, completion, cost = sums.get(job.id, (0, 0.0, 0, 0, 0.0))
        duration = (job.finished_at - job.started_at).total_seconds() if job.finished_at and job.started_at else None
        runs.append(
            JobRunResponseDTO(
                job_id=job.id,
                started_at=job.started_at,
                status=job.status,
                duration_seconds=round(duration, 2) if duration is not None else None,
                documents=documents,
                items=items,
                llm_calls=calls,
                llm_latency_ms=round(latency, 1),
                prompt_tokens=prompt,
                completion_tokens=completion,
                cost_usd=cost,
            )
        )
    return runs


def _last_hours(timezone: str) -> list[datetime]:
    """24 đầu giờ gần nhất (theo múi giờ ứng dụng, không có tzinfo), cũ trước mới sau; giờ hiện tại là phần tử cuối."""
    now = datetime.now(ZoneInfo(timezone)).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    return [now - timedelta(hours=23 - index) for index in range(24)]


async def _cost_groups(
    session: AsyncSession,
    *,
    scope: list[Any],
    timezone: str,
    dates: list[date],
    start: datetime,
    hours: list[datetime],
) -> list[CostGroupResponseDTO]:
    """Chi phí theo ngày và theo giờ của hai khoản: tải tài liệu lên (`ingest.*`: embedding BGE-M3 và đọc cấu trúc) và tạo task."""
    group = case(
        (LlmCall.operation.like("ingest.%"), "upload"),
        (LlmCall.operation == "task.proposal", "tasks"),
        else_=None,
    )
    local = func.timezone(timezone, LlmCall.created_at)
    day = cast(local, Date)
    hour = func.date_trunc("hour", local)
    since = min(start, datetime.now(ZoneInfo(timezone)) - timedelta(hours=25))
    rows = (
        await session.execute(
            select(group, day, hour, func.count(), func.coalesce(func.sum(LlmCall.cost_usd), 0.0))
            .where(LlmCall.created_at >= since, group.is_not(None), *scope)
            .group_by(group, day, hour)
        )
    ).all()
    result: list[CostGroupResponseDTO] = []
    for key in ("upload", "tasks"):
        mine = [row for row in rows if row[0] == key]
        in_days = [row for row in mine if row[1] in dates]
        result.append(
            CostGroupResponseDTO(
                key=key,
                calls=sum(int(row[3]) for row in in_days),
                cost_usd=sum(float(row[4]) for row in in_days),
                cost_per_day=[sum(float(row[4]) for row in mine if row[1] == d) for d in dates],
                cost_per_hour=[sum(float(row[4]) for row in mine if row[2] == slot) for slot in hours],
            )
        )
    return result


async def _providers(
    session: AsyncSession,
    *,
    scope: list[Any],
    day: Any,
    errors: Any,
    start: datetime,
    dates: list[date],
    hours: list[datetime],
    timezone: str,
) -> list[ProviderBreakdownResponseDTO]:
    totals = (
        await session.execute(
            select(
                LlmCall.provider,
                LlmCall.kind,
                func.count(),
                errors,
                func.percentile_cont(0.5).within_group(LlmCall.latency_ms),
                func.percentile_cont(0.95).within_group(LlmCall.latency_ms),
                func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
                func.coalesce(func.sum(LlmCall.completion_tokens), 0),
                func.coalesce(func.sum(LlmCall.input_count), 0),
                func.coalesce(func.sum(LlmCall.latency_ms), 0.0),
                func.coalesce(func.sum(LlmCall.cost_usd), 0.0),
            )
            .where(LlmCall.created_at >= start, *scope)
            .group_by(LlmCall.provider, LlmCall.kind)
            .order_by(LlmCall.kind.desc(), LlmCall.provider)
        )
    ).all()
    daily = (
        await session.execute(
            select(LlmCall.provider, day, func.coalesce(func.sum(LlmCall.cost_usd), 0.0))
            .where(LlmCall.created_at >= start, *scope)
            .group_by(LlmCall.provider, day)
        )
    ).all()
    hour = func.date_trunc("hour", func.timezone(timezone, LlmCall.created_at))
    since = datetime.now(ZoneInfo(timezone)) - timedelta(hours=25)
    hourly = (
        await session.execute(
            select(LlmCall.provider, hour, func.coalesce(func.sum(LlmCall.cost_usd), 0.0))
            .where(LlmCall.created_at >= since, *scope)
            .group_by(LlmCall.provider, hour)
        )
    ).all()
    result: list[ProviderBreakdownResponseDTO] = []
    for provider, kind, calls, errs, p50, p95, pt, ct, ic, latency, cost in totals:
        per_day = _per_day([(d, c) for p, d, c in daily if p == provider], dates, as_float=True)
        result.append(
            ProviderBreakdownResponseDTO(
                provider=provider,
                kind=kind,
                calls=int(calls),
                errors=int(errs or 0),
                p50_latency_ms=float(p50 or 0),
                p95_latency_ms=float(p95 or 0),
                prompt_tokens=int(pt),
                completion_tokens=int(ct),
                input_count=int(ic),
                gpu_seconds=float(latency) / 1000,
                cost_usd=float(cost),
                cost_per_day=per_day,
                cost_per_hour=[
                    float(next((c for p, h, c in hourly if p == provider and h == slot), 0.0)) for slot in hours
                ],
            )
        )
    return result


async def _ai(
    session: AsyncSession, *, scoped_users: list[int] | None, dates: list[date], start: datetime, timezone: str
) -> AiAnalyticsResponseDTO:
    if scoped_users is not None and not scoped_users:
        return _empty_ai(dates)
    scope = [] if scoped_users is None else [LlmCall.user_id.in_(scoped_users)]
    day = _local_day(LlmCall.created_at, timezone)
    errors = func.sum(case((LlmCall.ok.is_(False), 1), else_=0))
    daily = (
        await session.execute(
            select(day, func.count(), errors, func.coalesce(func.sum(LlmCall.cost_usd), 0.0))
            .where(LlmCall.created_at >= start, *scope)
            .group_by(day)
        )
    ).all()
    by_operation = (
        await session.execute(
            select(
                LlmCall.operation,
                LlmCall.kind,
                func.count(),
                errors,
                func.percentile_cont(0.5).within_group(LlmCall.latency_ms),
                func.percentile_cont(0.95).within_group(LlmCall.latency_ms),
                func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
                func.coalesce(func.sum(LlmCall.completion_tokens), 0),
                func.coalesce(func.sum(LlmCall.input_count), 0),
                func.coalesce(func.sum(LlmCall.cost_usd), 0.0),
            )
            .where(LlmCall.created_at >= start, *scope)
            .group_by(LlmCall.operation, LlmCall.kind)
            .order_by(func.sum(LlmCall.cost_usd).desc(), LlmCall.operation)
        )
    ).all()
    operations = [
        OperationBreakdownResponseDTO(
            operation=op,
            kind=kind,
            calls=int(calls),
            errors=int(errs or 0),
            p50_latency_ms=float(p50 or 0),
            p95_latency_ms=float(p95 or 0),
            prompt_tokens=int(pt),
            completion_tokens=int(ct),
            input_count=int(ic),
            cost_usd=float(cost),
        )
        for op, kind, calls, errs, p50, p95, pt, ct, ic, cost in by_operation
    ]
    hours = _last_hours(timezone)
    providers = await _providers(
        session, scope=scope, day=day, errors=errors, start=start, dates=dates, hours=hours, timezone=timezone
    )
    return AiAnalyticsResponseDTO(
        calls=sum(o.calls for o in operations),
        errors=sum(o.errors for o in operations),
        cost_usd=sum(o.cost_usd for o in operations),
        calls_per_day=_per_day([(d, c) for d, c, _, _ in daily], dates),
        errors_per_day=_per_day([(d, e or 0) for d, _, e, _ in daily], dates),
        cost_per_day=_per_day([(d, cost) for d, _, _, cost in daily], dates, as_float=True),
        by_operation=operations,
        by_provider=providers,
        cost_groups=await _cost_groups(session, scope=scope, timezone=timezone, dates=dates, start=start, hours=hours),
        hours=[hour.strftime("%Y-%m-%dT%H:00") for hour in hours],
        task_runs=await _runs(session, JobKind.AI_TASK_PROPOSAL, scoped_users=scoped_users, start=start),
        activation_runs=await _runs(session, JobKind.ACTIVATE_VERSION, scoped_users=scoped_users, start=start),
    )


async def build_analytics(session: AsyncSession, user: User, *, days: int, timezone: str) -> PortalAnalyticsResponseDTO:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()
    dates = [today - timedelta(days=days - 1 - index) for index in range(days)]
    start = datetime.combine(dates[0], time.min, tzinfo=tz).astimezone(UTC)
    admin = user.role == UserRole.ADMIN
    team_id, team_name = await _scope_team(session, user)

    scoped_users: list[int] | None = None
    if not admin:
        member_ids = (
            await session.scalars(select(TeamMember.user_id).where(TeamMember.team_id == team_id))
            if team_id is not None
            else None
        )
        scoped_users = [int(value) for value in member_ids.all()] if member_ids is not None else []

    return PortalAnalyticsResponseDTO(
        days=days,
        dates=[day.isoformat() for day in dates],
        scope="ALL" if admin else "TEAM",
        team_name=team_name,
        generated_at=datetime.now(UTC),
        people=await _people(session, team_id=team_id, admin=admin, dates=dates, start=start, timezone=timezone),
        documents=await _documents(session, today),
        viga=await _viga(session, scoped_users=scoped_users, dates=dates, start=start, timezone=timezone),
        tickets=await _tickets(session, team_id=team_id, admin=admin, dates=dates, start=start, timezone=timezone),
        ai=await _ai(session, scoped_users=scoped_users, dates=dates, start=start, timezone=timezone),
    )
