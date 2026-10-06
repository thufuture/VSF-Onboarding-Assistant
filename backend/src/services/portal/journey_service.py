"""State machine EmployeeTask — plan-portal/P2/P2.md mục 2, và lộ trình RIÊNG của từng nhân viên.

Chỉ chạm 3 trạng thái: LOCKED, READY, DONE. Các trạng thái còn lại (IN_PROGRESS, WAITING_EXTERNAL,
BLOCKED, SKIPPED) để dành cho Viga/ticket (P5/P7), P2 không có đường nào set chúng.

Lộ trình của nhân viên là BẢN SAO độc lập (kế hoạch plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md):
nhân viên bấm "Tạo lộ trình" thì sao chép các phiên bản `APPLIED` của các ngày và có hiệu lực ngay (không nháp). Sau đó HR sửa
hay áp dụng bản mới ở Quản lý task KHÔNG đổi lộ trình này; nhân viên được báo và tự bấm "Cập nhật" (`rollout_service`).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.employee_journey import EmployeeJourney
from src.model.employee_stage import EmployeeStage
from src.model.employee_task import EmployeeTask
from src.model.employee_task_dependency import EmployeeTaskDependency
from src.model.enums import EmployeeTaskStatus, JourneyTemplateStatus, StageVersionStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.stage_version import StageVersion
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


async def team_id_of(session: AsyncSession, user_id: int) -> int | None:
    """Team của một người (HR dùng để kiểm phạm vi trước khi thêm lộ trình cho nhân viên)."""
    return await _current_team_id(session, user_id)


async def _find_journey_template(session: AsyncSession, team_id: int | None) -> JourneyTemplate | None:
    """1 template đã áp dụng (PUBLISHED) khớp team của user; ưu tiên template riêng của team trước template dùng chung."""
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


async def _copy_applied_stages(session: AsyncSession, journey: EmployeeJourney, template: JourneyTemplate) -> int:
    """Sao chép phiên bản `APPLIED` của từng ngày thành bản sao riêng. Trả số việc đã sao chép."""
    rows = (
        await session.execute(
            select(JourneyStage, StageVersion)
            .join(StageVersion, StageVersion.journey_stage_id == JourneyStage.id)
            .where(
                JourneyStage.journey_template_id == template.id,
                StageVersion.status == StageVersionStatus.APPLIED.value,
            )
            .order_by(JourneyStage.sort_order, JourneyStage.id)
        )
    ).all()
    total = 0
    for stage, version in rows:
        tasks = (
            await session.scalars(
                select(TaskTemplate)
                .where(TaskTemplate.stage_version_id == version.id)
                .order_by(TaskTemplate.sort_order, TaskTemplate.id)
            )
        ).all()
        if not tasks:
            continue
        employee_stage = EmployeeStage(
            employee_journey_id=journey.id,
            journey_stage_id=stage.id,
            source_stage_version_id=version.id,
            title=stage.title,
            sort_order=stage.sort_order,
        )
        session.add(employee_stage)
        await session.flush()
        copies: dict[int, EmployeeTask] = {}
        for task in tasks:
            copy = EmployeeTask(
                employee_journey_id=journey.id,
                employee_stage_id=employee_stage.id,
                source_task_template_id=task.id,
                origin_key=task.origin_key,
                title=task.title,
                body_markdown=task.body_markdown,
                required=task.required,
                task_group=task.task_group,
                sort_order=task.sort_order,
                team_id=journey.team_id,
                status=EmployeeTaskStatus.READY.value,
            )
            session.add(copy)
            copies[task.id] = copy
        await session.flush()
        edges = (
            await session.scalars(select(TaskDependency).where(TaskDependency.task_template_id.in_(list(copies))))
        ).all()
        for edge in edges:
            target, source = copies.get(edge.task_template_id), copies.get(edge.depends_on_task_template_id)
            if target is None or source is None:
                continue
            session.add(EmployeeTaskDependency(employee_task_id=target.id, depends_on_employee_task_id=source.id))
            target.status = EmployeeTaskStatus.LOCKED.value  # có tiên quyết thì khóa, không thì làm được ngay
        total += len(copies)
    return total


async def _active_journey(session: AsyncSession, user_id: int) -> EmployeeJourney | None:
    result: EmployeeJourney | None = await session.scalar(
        select(EmployeeJourney)
        .where(EmployeeJourney.user_id == user_id, EmployeeJourney.deleted_at.is_(None))
        .order_by(EmployeeJourney.id.desc())
        .limit(1)
    )
    return result


async def get_journey(session: AsyncSession, user: User) -> EmployeeJourney | None:
    """Lộ trình đang hoạt động của `user`, hoặc `None` nếu người này chưa bấm "Tạo lộ trình"."""
    return await _active_journey(session, user.id)


async def create_journey(session: AsyncSession, user: User) -> tuple[EmployeeJourney, bool]:
    """Tạo lộ trình RIÊNG cho `user` từ các bản đang áp dụng (có hiệu lực ngay). Idempotent: đã có thì trả lại cái cũ.

    Trả (lộ trình, vừa tạo mới?).
    """
    user_id = user.id  # lấy trước: sau rollback đối tượng `user` hết hạn và đọc lại ngoài ngữ cảnh async sẽ lỗi
    existing = await _active_journey(session, user_id)
    if existing is not None:
        return existing, False
    team_id = await _current_team_id(session, user_id)
    if team_id is None:
        raise PortalError(409, "NO_TEAM_ASSIGNED", "portal.no_team_assigned")
    template = await _find_journey_template(session, team_id)
    if template is None:
        raise PortalError(404, "NO_JOURNEY_TEMPLATE", "portal.no_journey_template")
    journey = EmployeeJourney(user_id=user_id, journey_template_id=template.id, team_id=team_id)
    session.add(journey)
    try:
        await session.flush()
    except IntegrityError:
        # Hai yêu cầu cùng lúc: index duy nhất chỉ giữ một lộ trình; yêu cầu thua lấy lại cái của yêu cầu thắng.
        await session.rollback()
        existing = await _active_journey(session, user_id)
        if existing is None:
            raise
        return existing, False
    copied = await _copy_applied_stages(session, journey, template)
    if not copied:
        await session.rollback()
        raise PortalError(404, "NO_JOURNEY_TEMPLATE", "portal.no_journey_template")
    await session.commit()
    return journey, True


async def unlock_dependents(session: AsyncSession, journey_id: int) -> None:
    """Việc đang khóa mà mọi tiên quyết (trong bản sao) đã xong thì làm được ngay."""
    locked_tasks = (
        await session.scalars(
            select(EmployeeTask).where(
                EmployeeTask.employee_journey_id == journey_id,
                EmployeeTask.status == EmployeeTaskStatus.LOCKED,
                EmployeeTask.deleted_at.is_(None),
            )
        )
    ).all()
    if not locked_tasks:
        return
    all_tasks = (
        await session.scalars(
            select(EmployeeTask).where(
                EmployeeTask.employee_journey_id == journey_id, EmployeeTask.deleted_at.is_(None)
            )
        )
    ).all()
    done_ids = {t.id for t in all_tasks if t.status == EmployeeTaskStatus.DONE}
    for candidate in locked_tasks:
        prerequisite_ids = (
            await session.scalars(
                select(EmployeeTaskDependency.depends_on_employee_task_id).where(
                    EmployeeTaskDependency.employee_task_id == candidate.id
                )
            )
        ).all()
        if prerequisite_ids and all(dep_id in done_ids for dep_id in prerequisite_ids):
            candidate.status = EmployeeTaskStatus.READY


async def complete_task(session: AsyncSession, user: User, employee_task_id: int) -> EmployeeTask:
    """P0A D1: 1 hành động duy nhất cho cả task, không có sub-step/duyệt. Idempotent nếu đã DONE."""
    task = await session.get(EmployeeTask, employee_task_id)
    if task is None or task.deleted_at is not None:
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
    await unlock_dependents(session, journey.id)
    await session.commit()
    return task


@dataclass
class TaskDetail:
    """Một việc trong lộ trình riêng kèm ngày của nó — đủ dữ liệu cho UI vẽ roadmap (mọi chữ lấy từ bản sao)."""

    task: EmployeeTask
    stage: EmployeeStage


async def list_task_details(session: AsyncSession, journey_id: int) -> list[TaskDetail]:
    rows = await session.execute(
        select(EmployeeTask, EmployeeStage)
        .join(EmployeeStage, EmployeeStage.id == EmployeeTask.employee_stage_id)
        .where(
            EmployeeTask.employee_journey_id == journey_id,
            EmployeeTask.deleted_at.is_(None),
            EmployeeStage.deleted_at.is_(None),
        )
        .order_by(EmployeeStage.sort_order, EmployeeStage.id, EmployeeTask.sort_order, EmployeeTask.id)
    )
    return [TaskDetail(task, stage) for task, stage in rows.all()]


async def list_prerequisites(session: AsyncSession, journey_id: int) -> dict[int, list[tuple[str, bool]]]:
    """Tiên quyết của từng task trong journey: `employee_task.id -> [(tên task tiên quyết, đã xong?)]`."""
    tasks = (
        await session.scalars(
            select(EmployeeTask).where(
                EmployeeTask.employee_journey_id == journey_id, EmployeeTask.deleted_at.is_(None)
            )
        )
    ).all()
    by_id = {t.id: t for t in tasks}
    if not by_id:
        return {}
    rows = (
        await session.execute(
            select(EmployeeTaskDependency.employee_task_id, EmployeeTaskDependency.depends_on_employee_task_id).where(
                EmployeeTaskDependency.employee_task_id.in_(list(by_id))
            )
        )
    ).all()
    result: dict[int, list[tuple[str, bool]]] = {}
    for task_id, depends_on_id in rows:
        source = by_id.get(depends_on_id)
        if source is None:
            continue
        result.setdefault(task_id, []).append((source.title, source.status == EmployeeTaskStatus.DONE))
    return result
