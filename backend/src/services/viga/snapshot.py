"""Ảnh chụp tình hình của người hỏi, tính tại chỗ từ lộ trình THẬT bằng truy vấn DB nhẹ (không LLM) — mục 15.3b.

Chỉ đọc đúng lộ trình của chính người đang đăng nhập (`user_id` lấy từ phiên). Dữ liệu đi ra dịch vụ LLM bên ngoài chỉ gồm
mã việc, tên việc, trạng thái và tên ngày (`llm_view`); tên, email, phòng ban của nhân viên không bao giờ nằm trong đó
(quyết định 3, mục 0.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import EmployeeTaskStatus
from src.model.task_dependency import TaskDependency
from src.model.user import User
from src.services.portal import journey_service
from src.services.portal.errors import PortalError

# Việc nhân viên "vừa mở" còn hiệu lực trong bao lâu (quyết định 6, mục 0.1).
LAST_OPENED_WINDOW = timedelta(minutes=30)


@dataclass(frozen=True)
class SnapshotTask:
    id: int  # employee_tasks.id (mã việc của chính người hỏi)
    title: str
    status: str
    stage_id: int
    stage_title: str
    stage_sort: int
    sort_order: int
    required: bool
    body_markdown: str
    prerequisite_ids: tuple[int, ...] = ()

    @property
    def state(self) -> str:
        """done | ready | locked: máy trạng thái việc chỉ có LOCKED, READY, DONE (không có "đang làm")."""
        if self.status == EmployeeTaskStatus.DONE:
            return "done"
        if self.status == EmployeeTaskStatus.READY:
            return "ready"
        return "locked"


@dataclass(frozen=True)
class SnapshotDay:
    stage_id: int
    title: str
    tasks: tuple[SnapshotTask, ...]

    @property
    def done(self) -> int:
        return sum(1 for task in self.tasks if task.state == "done")

    @property
    def total(self) -> int:
        return len(self.tasks)

    @property
    def ready(self) -> list[SnapshotTask]:
        return [task for task in self.tasks if task.state == "ready"]


@dataclass(frozen=True)
class JourneySnapshot:
    journey_id: int
    tasks: tuple[SnapshotTask, ...]
    last_opened_task_id: int | None = None
    last_opened_at: datetime | None = None
    _by_id: dict[int, SnapshotTask] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_id", {task.id: task for task in self.tasks})

    def get(self, task_id: int) -> SnapshotTask | None:
        return self._by_id.get(task_id)

    @property
    def done(self) -> int:
        return sum(1 for task in self.tasks if task.state == "done")

    @property
    def total(self) -> int:
        return len(self.tasks)

    @property
    def percent(self) -> int:
        return round(100 * self.done / self.total) if self.total else 0

    @property
    def days(self) -> list[SnapshotDay]:
        order: dict[int, list[SnapshotTask]] = {}
        for task in self.tasks:  # `tasks` đã sắp theo ngày rồi số thứ tự
            order.setdefault(task.stage_id, []).append(task)
        return [SnapshotDay(stage_id, rows[0].stage_title, tuple(rows)) for stage_id, rows in order.items()]

    @property
    def current_day(self) -> SnapshotDay | None:
        days = self.days
        return next((day for day in days if day.done < day.total), days[-1] if days else None)

    def ready_tasks(self) -> list[SnapshotTask]:
        """Việc làm được ngay, bắt buộc trước, theo thứ tự ngày rồi số thứ tự."""
        ready = [task for task in self.tasks if task.state == "ready"]
        return sorted(ready, key=lambda task: (not task.required, task.stage_sort, task.sort_order, task.id))

    def last_opened(self, now: datetime) -> SnapshotTask | None:
        if self.last_opened_task_id is None or self.last_opened_at is None:
            return None
        if now - self.last_opened_at > LAST_OPENED_WINDOW:
            return None
        return self.get(self.last_opened_task_id)

    def llm_view(self) -> str:
        """Phần tối thiểu gửi cho LLM định tuyến: mã việc, tên việc, trạng thái, tên ngày. Không có dữ liệu cá nhân."""
        return "\n".join(f"id={t.id} | {t.title} | {t.status} | {t.stage_title}" for t in self.tasks)


async def load_snapshot(session: AsyncSession, user: User, *, start_if_missing: bool = True) -> JourneySnapshot | None:
    """Ảnh chụp lộ trình của `user`; `None` nếu người này chưa có lộ trình và không tạo được."""
    try:
        journey = await journey_service.get_or_start_journey(session, user) if start_if_missing else None
    except PortalError:
        return None
    if journey is None:
        return None
    details = await journey_service.list_task_details(session, journey.id)
    by_template = {d.task.task_template_id: d.task.id for d in details}
    dependency_rows = (
        await session.execute(
            select(TaskDependency.task_template_id, TaskDependency.depends_on_task_template_id).where(
                TaskDependency.task_template_id.in_(list(by_template))
            )
        )
        if by_template
        else None
    )
    prerequisites: dict[int, list[int]] = {}
    for template_id, depends_on in dependency_rows.all() if dependency_rows is not None else []:
        target, source = by_template.get(template_id), by_template.get(depends_on)
        if target is not None and source is not None:
            prerequisites.setdefault(target, []).append(source)
    tasks = tuple(
        SnapshotTask(
            id=d.task.id,
            title=d.template.title,
            status=d.task.status,
            stage_id=d.stage.id,
            stage_title=d.stage.title,
            stage_sort=d.stage.sort_order,
            sort_order=d.template.sort_order,
            required=d.template.required,
            body_markdown=d.template.body_markdown,
            prerequisite_ids=tuple(prerequisites.get(d.task.id, ())),
        )
        for d in details
    )
    fresh: EmployeeJourney | None = await session.get(EmployeeJourney, journey.id)
    return JourneySnapshot(
        journey_id=journey.id,
        tasks=tasks,
        last_opened_task_id=fresh.last_opened_task_id if fresh else None,
        last_opened_at=fresh.last_opened_at if fresh else None,
    )


async def mark_task_opened(session: AsyncSession, user: User, employee_task_id: int) -> None:
    """Ghi "việc vừa mở" (mục 15.3e). Chỉ nhận việc thuộc lộ trình của chính người gọi; việc khác trả 404."""
    task = await session.get(EmployeeTask, employee_task_id)
    journey = await session.get(EmployeeJourney, task.employee_journey_id) if task is not None else None
    if task is None or journey is None or journey.user_id != user.id:
        raise PortalError(404, "TASK_NOT_FOUND", "portal.task_not_found")
    journey.last_opened_task_id = task.id
    journey.last_opened_at = datetime.now(UTC)
    await session.commit()
