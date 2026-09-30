"""Danh sách nhân viên trong phạm vi team của HR, kèm tiến độ lộ trình — dùng lại bảng đã có
(users/team_members/employee_journeys/employee_tasks), không thêm bảng mới."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import EmployeeTaskStatus, UserRole
from src.model.journey_stage import JourneyStage
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User

# Ưu tiên hiển thị task "đang có vấn đề" trước — khớp cách v15 tô màu trạng thái nhân viên.
_STATUS_PRIORITY = [
    EmployeeTaskStatus.BLOCKED,
    EmployeeTaskStatus.WAITING_EXTERNAL,
    EmployeeTaskStatus.IN_PROGRESS,
    EmployeeTaskStatus.READY,
]


@dataclass
class EmployeeSummary:
    id: int
    display_name: str
    email: str
    department: str | None
    journey_started: bool
    tasks_done: int
    tasks_total: int
    current_task_title: str | None
    current_stage_title: str | None
    current_status: str | None


async def list_employees(session: AsyncSession, *, team_id: int | None) -> list[EmployeeSummary]:
    """Nhân viên (USER) trong team của HR — ADMIN (team_id=None) không liệt kê vì không có phạm vi chung."""
    if team_id is None:
        return []
    team_name = await session.scalar(select(Team.name).where(Team.id == team_id))
    users = (
        await session.scalars(
            select(User)
            .join(TeamMember, TeamMember.user_id == User.id)
            .where(TeamMember.team_id == team_id, User.role == UserRole.USER)
            .order_by(User.display_name)
        )
    ).all()

    summaries: list[EmployeeSummary] = []
    for user in users:
        journey = await session.scalar(
            select(EmployeeJourney)
            .where(EmployeeJourney.user_id == user.id, EmployeeJourney.deleted_at.is_(None))
            .order_by(EmployeeJourney.id.desc())
            .limit(1)
        )
        tasks_done = 0
        tasks_total = 0
        current_task_title: str | None = None
        current_stage_title: str | None = None
        current_status: str | None = None
        if journey is not None:
            tasks_total = (
                await session.scalar(
                    select(func.count(EmployeeTask.id)).where(EmployeeTask.employee_journey_id == journey.id)
                )
                or 0
            )
            tasks_done = (
                await session.scalar(
                    select(func.count(EmployeeTask.id)).where(
                        EmployeeTask.employee_journey_id == journey.id,
                        EmployeeTask.status == EmployeeTaskStatus.DONE,
                    )
                )
                or 0
            )
            for status in _STATUS_PRIORITY:
                row = (
                    await session.execute(
                        select(EmployeeTask, TaskTemplate, JourneyStage)
                        .join(TaskTemplate, TaskTemplate.id == EmployeeTask.task_template_id)
                        .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
                        .where(EmployeeTask.employee_journey_id == journey.id, EmployeeTask.status == status)
                        .order_by(JourneyStage.sort_order, TaskTemplate.sort_order)
                        .limit(1)
                    )
                ).first()
                if row is not None:
                    _, template, stage = row
                    current_task_title = template.title
                    current_stage_title = stage.title
                    current_status = status.value
                    break
        summaries.append(
            EmployeeSummary(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                department=team_name,
                journey_started=journey is not None,
                tasks_done=tasks_done,
                tasks_total=tasks_total,
                current_task_title=current_task_title,
                current_stage_title=current_stage_title,
                current_status=current_status,
            )
        )
    return summaries
