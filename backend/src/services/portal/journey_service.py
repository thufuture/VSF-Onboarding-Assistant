"""State machine EmployeeTask — plan-portal/P2/P2.md mục 2.

Chỉ chạm 3 trạng thái: LOCKED, READY, DONE. Các trạng thái còn lại (IN_PROGRESS, WAITING_EXTERNAL,
BLOCKED, SKIPPED) để dành cho Viga/ticket (P5/P7), P2 không có đường nào set chúng.
"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import EmployeeTaskStatus, JourneyTemplateStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.task_dependency import TaskDependency
from src.model.task_template import TaskTemplate
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.portal.errors import PortalError


async def _current_team_id(session: AsyncSession, user_id: int) -> int | None:
    """Team đầu tiên (theo id) mà user thuộc — Portal coi mỗi user chỉ ở 1 team (P1/P1.md mục 0)."""
    return cast(
        "int | None",
        await session.scalar(
            select(TeamMember.team_id).where(TeamMember.user_id == user_id).order_by(TeamMember.team_id).limit(1)
        ),
    )


async def _find_journey_template(session: AsyncSession, team_id: int | None) -> JourneyTemplate | None:
    """1 template PUBLISHED khớp team của user; ưu tiên template riêng của team trước template dùng chung."""
    if team_id is not None:
        scoped = await session.scalar(
            select(JourneyTemplate)
            .where(JourneyTemplate.status == JourneyTemplateStatus.PUBLISHED, JourneyTemplate.team_id == team_id)
            .order_by(JourneyTemplate.id)
            .limit(1)
        )
        if scoped is not None:
            return scoped
    return cast(
        "JourneyTemplate | None",
        await session.scalar(
            select(JourneyTemplate)
            .where(JourneyTemplate.status == JourneyTemplateStatus.PUBLISHED, JourneyTemplate.team_id.is_(None))
            .order_by(JourneyTemplate.id)
            .limit(1)
        ),
    )


async def _start_journey(session: AsyncSession, user: User, template: JourneyTemplate, team_id: int) -> EmployeeJourney:
    """P0A D2: snapshot 1 lần từ template hiện có — publish version mới sau đó không ảnh hưởng journey này."""
    journey = EmployeeJourney(user_id=user.id, journey_template_id=template.id, team_id=team_id)
    session.add(journey)
    await session.flush()

    task_templates = (
        await session.scalars(
            select(TaskTemplate)
            .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
            .where(JourneyStage.journey_template_id == template.id)
        )
    ).all()
    if not task_templates:
        await session.commit()
        return journey

    template_ids = [t.id for t in task_templates]
    dependency_rows = (
        await session.scalars(
            select(TaskDependency.task_template_id).where(TaskDependency.task_template_id.in_(template_ids))
        )
    ).all()
    has_dependency = set(dependency_rows)

    for task_template in task_templates:
        status = EmployeeTaskStatus.LOCKED if task_template.id in has_dependency else EmployeeTaskStatus.READY
        session.add(
            EmployeeTask(
                employee_journey_id=journey.id,
                task_template_id=task_template.id,
                team_id=team_id,
                status=status,
            )
        )
    await session.commit()
    return journey


async def get_or_start_journey(session: AsyncSession, user: User) -> EmployeeJourney:
    """Trả journey đang hoạt động của `user`; tự tạo nếu chưa có (P2.md mục 1)."""
    existing = await session.scalar(
        select(EmployeeJourney)
        .where(EmployeeJourney.user_id == user.id, EmployeeJourney.deleted_at.is_(None))
        .order_by(EmployeeJourney.id.desc())
        .limit(1)
    )
    if existing is not None:
        return existing

    team_id = await _current_team_id(session, user.id)
    if team_id is None:
        raise PortalError(409, "NO_TEAM_ASSIGNED", "portal.no_team_assigned")
    template = await _find_journey_template(session, team_id)
    if template is None:
        raise PortalError(404, "NO_JOURNEY_TEMPLATE", "portal.no_journey_template")
    return await _start_journey(session, user, template, team_id)


async def _unlock_dependents(session: AsyncSession, journey_id: int, completed_template_id: int) -> None:
    locked_tasks = (
        await session.scalars(
            select(EmployeeTask).where(
                EmployeeTask.employee_journey_id == journey_id, EmployeeTask.status == EmployeeTaskStatus.LOCKED
            )
        )
    ).all()
    if not locked_tasks:
        return

    all_tasks = (
        await session.scalars(select(EmployeeTask).where(EmployeeTask.employee_journey_id == journey_id))
    ).all()
    done_template_ids = {t.task_template_id for t in all_tasks if t.status == EmployeeTaskStatus.DONE}

    for candidate in locked_tasks:
        prerequisite_ids = (
            await session.scalars(
                select(TaskDependency.depends_on_task_template_id).where(
                    TaskDependency.task_template_id == candidate.task_template_id
                )
            )
        ).all()
        if prerequisite_ids and all(dep_id in done_template_ids for dep_id in prerequisite_ids):
            candidate.status = EmployeeTaskStatus.READY


async def complete_task(session: AsyncSession, user: User, employee_task_id: int) -> EmployeeTask:
    """P0A D1: 1 hành động duy nhất cho cả task, không có sub-step/duyệt. Idempotent nếu đã DONE."""
    task = await session.get(EmployeeTask, employee_task_id)
    if task is None:
        raise PortalError(404, "TASK_NOT_FOUND", "portal.task_not_found")

    journey = await session.get(EmployeeJourney, task.employee_journey_id)
    if journey is None or journey.user_id != user.id:
        # Không lộ việc task này có tồn tại hay không cho người không sở hữu (giống auth_service).
        raise PortalError(404, "TASK_NOT_FOUND", "portal.task_not_found")

    if task.status == EmployeeTaskStatus.DONE:
        return task
    if task.status != EmployeeTaskStatus.READY:
        raise PortalError(409, "TASK_LOCKED", "portal.task_locked")

    task.status = EmployeeTaskStatus.DONE
    task.completed_at = datetime.now(UTC)
    await session.flush()
    await _unlock_dependents(session, journey.id, task.task_template_id)
    await session.commit()
    return task


class TaskDetail:
    """Kết quả join EmployeeTask + TaskTemplate + JourneyStage — đủ dữ liệu cho UI vẽ roadmap."""

    def __init__(self, task: EmployeeTask, template: TaskTemplate, stage: JourneyStage) -> None:
        self.task = task
        self.template = template
        self.stage = stage


async def list_task_details(session: AsyncSession, journey_id: int) -> list[TaskDetail]:
    rows = await session.execute(
        select(EmployeeTask, TaskTemplate, JourneyStage)
        .join(TaskTemplate, TaskTemplate.id == EmployeeTask.task_template_id)
        .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
        .where(EmployeeTask.employee_journey_id == journey_id)
        .order_by(JourneyStage.sort_order, TaskTemplate.sort_order, EmployeeTask.id)
    )
    return [TaskDetail(task, template, stage) for task, template, stage in rows.all()]
