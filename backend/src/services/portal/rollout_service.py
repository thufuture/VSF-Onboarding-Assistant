"""HR áp dụng một phiên bản mới: báo cho nhân viên và để NHÂN VIÊN tự bấm "Cập nhật".

Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md mục 4.5.
- Áp dụng KHÔNG đổi dữ liệu lộ trình của ai: chỉ ghi `journey_change_notices` và `employee_task_changes` (PENDING).
- Thay đổi tính theo CHÍNH bản sao hiện tại của nhân viên so với bản mới (so theo `origin_key`), nên áp dụng liên tiếp v3 rồi v4
  chỉ còn một thay đổi đúng (dòng PENDING cũ thành SUPERSEDED).
- "Cập nhật" thay nội dung việc bằng bản mới nhất và GIỮ NGUYÊN trạng thái (việc đã xong vẫn đã xong); việc chưa làm được tính lại khóa.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.employee_journey import EmployeeJourney
from src.model.employee_stage import EmployeeStage
from src.model.employee_task import EmployeeTask
from src.model.employee_task_change import EmployeeTaskChange
from src.model.employee_task_dependency import EmployeeTaskDependency
from src.model.enums import ChangeKind, ChangeStatus, EmployeeTaskStatus, StageVersionStatus
from src.model.journey_change_notice import JourneyChangeNotice
from src.model.journey_stage import JourneyStage
from src.model.stage_version import StageVersion
from src.model.task_dependency import TaskDependency
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.portal.errors import PortalError
from src.services.portal.version_diff import TaskChange, TaskView, changed_fields, diff_tasks, summarize

AUTO_APPLIED_KINDS = (ChangeKind.ADDED, ChangeKind.REMOVED)  # tự áp dụng khi HR áp dụng bản mới
KEPT_DONE = "kept_done"  # việc đã làm bị bỏ ở bản mới: giữ nguyên, chỉ báo thông tin


# ───────────────────────────── Dựng TaskView ─────────────────────────────


async def task_views(session: AsyncSession, version_id: int) -> list[TaskView]:
    """Các việc của một phiên bản mẫu dưới dạng `TaskView` (tiên quyết đổi sang `origin_key`)."""
    tasks = (
        await session.scalars(
            select(TaskTemplate).where(TaskTemplate.stage_version_id == version_id).order_by(TaskTemplate.sort_order)
        )
    ).all()
    if not tasks:
        return []
    key_by_id = {task.id: task.origin_key for task in tasks}
    edges = (
        await session.execute(
            select(TaskDependency.task_template_id, TaskDependency.depends_on_task_template_id).where(
                TaskDependency.task_template_id.in_(list(key_by_id))
            )
        )
    ).all()
    prerequisites: dict[int, list[UUID]] = {}
    for task_id, depends_on in edges:
        if depends_on in key_by_id:
            prerequisites.setdefault(task_id, []).append(key_by_id[depends_on])
    return [
        TaskView(
            origin_key=task.origin_key,
            title=task.title,
            body_markdown=task.body_markdown,
            required=task.required,
            task_group=task.task_group,
            sort_order=task.sort_order,
            prerequisite_keys=tuple(sorted(prerequisites.get(task.id, []), key=str)),
            source_task_template_id=task.id,
        )
        for task in tasks
    ]


async def employee_views(session: AsyncSession, employee_stage_id: int | None) -> list[TaskView]:
    """Các việc (chưa xóa) của một ngày trong bản sao của nhân viên dưới dạng `TaskView`."""
    if employee_stage_id is None:
        return []
    tasks = (
        await session.scalars(
            select(EmployeeTask)
            .where(EmployeeTask.employee_stage_id == employee_stage_id, EmployeeTask.deleted_at.is_(None))
            .order_by(EmployeeTask.sort_order, EmployeeTask.id)
        )
    ).all()
    if not tasks:
        return []
    key_by_id = {task.id: task.origin_key for task in tasks}
    edges = (
        await session.execute(
            select(EmployeeTaskDependency.employee_task_id, EmployeeTaskDependency.depends_on_employee_task_id).where(
                EmployeeTaskDependency.employee_task_id.in_(list(key_by_id))
            )
        )
    ).all()
    prerequisites: dict[int, list[UUID]] = {}
    for task_id, depends_on in edges:
        if depends_on in key_by_id:
            prerequisites.setdefault(task_id, []).append(key_by_id[depends_on])
    return [
        TaskView(
            origin_key=task.origin_key,
            title=task.title,
            body_markdown=task.body_markdown,
            required=task.required,
            task_group=task.task_group,
            sort_order=task.sort_order,
            prerequisite_keys=tuple(sorted(prerequisites.get(task.id, []), key=str)),
            employee_task_id=task.id,
            status=task.status,
            source_task_template_id=task.source_task_template_id,
        )
        for task in tasks
    ]


async def _active_stage(session: AsyncSession, journey_id: int, journey_stage_id: int) -> EmployeeStage | None:
    result: EmployeeStage | None = await session.scalar(
        select(EmployeeStage)
        .where(
            EmployeeStage.employee_journey_id == journey_id,
            EmployeeStage.journey_stage_id == journey_stage_id,
            EmployeeStage.deleted_at.is_(None),
        )
        .order_by(EmployeeStage.id.desc())
        .limit(1)
    )
    return result


# ───────────────────────────── Khi HR áp dụng ─────────────────────────────


@dataclass
class _Affected:
    journey: EmployeeJourney
    stage: EmployeeStage | None
    changes: list[TaskChange]


async def _affected_journeys(session: AsyncSession, version: StageVersion) -> list[_Affected]:
    """Lộ trình bị ảnh hưởng bởi bản mới: cùng lộ trình mẫu, ngày đó chưa ở bản này, và có ít nhất một thay đổi."""
    stage = await session.get(JourneyStage, version.journey_stage_id)
    assert stage is not None
    journeys = (
        await session.scalars(
            select(EmployeeJourney).where(
                EmployeeJourney.journey_template_id == stage.journey_template_id, EmployeeJourney.deleted_at.is_(None)
            )
        )
    ).all()
    target = await task_views(session, version.id)
    result: list[_Affected] = []
    for journey in journeys:
        employee_stage = await _active_stage(session, journey.id, stage.id)
        if employee_stage is not None and employee_stage.source_stage_version_id == version.id:
            continue
        current = await employee_views(session, employee_stage.id if employee_stage else None)
        changes = diff_tasks(current, target)
        if changes or employee_stage is not None:
            result.append(_Affected(journey=journey, stage=employee_stage, changes=changes))
    return result


async def create_notices(session: AsyncSession, *, version: StageVersion, applied_by: int | None) -> int:
    """Ghi thông báo cho mọi nhân viên bị ảnh hưởng; trả số thông báo đã tạo. KHÔNG đổi lộ trình của ai."""
    now = datetime.now(UTC)
    created = 0
    for affected in await _affected_journeys(session, version):
        journey, employee_stage, changes = affected.journey, affected.stage, affected.changes
        # Thay đổi cũ chưa xử lý của cùng ngày được thay bằng thay đổi mới tính từ bản sao hiện tại.
        older = (
            await session.scalars(
                select(EmployeeTaskChange)
                .join(JourneyChangeNotice, JourneyChangeNotice.id == EmployeeTaskChange.notice_id)
                .where(
                    JourneyChangeNotice.employee_journey_id == journey.id,
                    JourneyChangeNotice.journey_stage_id == version.journey_stage_id,
                    EmployeeTaskChange.status == ChangeStatus.PENDING.value,
                )
            )
        ).all()
        for row in older:
            row.status = ChangeStatus.SUPERSEDED.value
            row.resolved_at = now
        if not changes:
            if employee_stage is not None:
                employee_stage.source_stage_version_id = version.id
            continue
        notice = JourneyChangeNotice(
            employee_journey_id=journey.id,
            user_id=journey.user_id,
            journey_stage_id=version.journey_stage_id,
            target_version_id=version.id,
            applied_by=applied_by,
            new_stage=employee_stage is None,
        )
        session.add(notice)
        await session.flush()
        automatic: list[EmployeeTaskChange] = []
        for change in changes:
            informational = change.informational
            row = EmployeeTaskChange(
                notice_id=notice.id,
                employee_task_id=change.employee_task_id,
                origin_key=change.origin_key,
                kind=change.kind.value,
                status=(ChangeStatus.DISMISSED if informational else ChangeStatus.PENDING).value,
                task_title=change.title,
                before=change.before,
                after={"note": KEPT_DONE} if informational else change.after,
                resolved_at=now if informational else None,
            )
            session.add(row)
            if not informational and change.kind in AUTO_APPLIED_KINDS:
                automatic.append(row)
        await session.flush()
        # Thêm việc (kể cả cả một ngày mới) và bỏ việc chỉ BÁO: nhân viên không có gì để quyết định nên áp dụng luôn.
        # Chỉ việc bị SỬA nội dung hoặc đổi tiên quyết mới chờ nhân viên xem và chấp nhận.
        if automatic:
            await _apply(session, notice, automatic, now=now)
        created += 1
    return created


@dataclass
class ApplyPreview:
    modified: int
    added: int
    removed: int
    employee_count: int
    has_applied_before: bool


async def preview_apply(session: AsyncSession, version: StageVersion) -> ApplyPreview:
    """Xem trước khi áp dụng (KHÔNG ghi gì): bao nhiêu việc đổi, thêm, bỏ và bao nhiêu nhân viên sẽ nhận thông báo."""
    applied = await session.scalar(
        select(StageVersion).where(
            StageVersion.journey_stage_id == version.journey_stage_id,
            StageVersion.status == StageVersionStatus.APPLIED.value,
            StageVersion.id != version.id,
        )
    )
    target = await task_views(session, version.id)
    before = await task_views(session, applied.id) if applied else []
    counts = summarize(diff_tasks(before, target))
    affected = [item for item in await _affected_journeys(session, version) if item.changes]
    return ApplyPreview(
        modified=counts["modified"],
        added=counts["added"],
        removed=counts["removed"],
        employee_count=len(affected),
        has_applied_before=applied is not None,
    )


# ───────────────────────────── Nhân viên xem thông báo ─────────────────────────────


@dataclass
class ChangeDetail:
    id: int
    notice_id: int
    kind: str
    status: str
    task_title: str
    employee_task_id: int | None
    employee_status: str | None
    stage_title: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    changed_fields: list[str]
    informational: bool


@dataclass
class NoticeDetail:
    id: int
    journey_stage_id: int | None
    stage_title: str
    version_no: int
    created_at: datetime
    read_at: datetime | None
    new_stage: bool = False
    changes: list[ChangeDetail] = field(default_factory=list)


def _is_informational(row: EmployeeTaskChange) -> bool:
    return bool(row.after and row.after.get("note") == KEPT_DONE)


def _fields_of(row: EmployeeTaskChange) -> list[str]:
    if row.before is None or row.after is None or _is_informational(row):
        return []
    probe = TaskChange(
        kind=ChangeKind(row.kind), origin_key=row.origin_key, title=row.task_title, before=row.before, after=row.after
    )
    return changed_fields(probe)


async def list_notices(session: AsyncSession, user: User, *, limit: int = 50) -> list[NoticeDetail]:
    notices = (
        await session.scalars(
            select(JourneyChangeNotice)
            .where(JourneyChangeNotice.user_id == user.id)
            .order_by(JourneyChangeNotice.id.desc())
            .limit(limit)
        )
    ).all()
    if not notices:
        return []
    notice_ids = [n.id for n in notices]
    rows = (
        await session.scalars(
            select(EmployeeTaskChange)
            .where(EmployeeTaskChange.notice_id.in_(notice_ids))
            .order_by(EmployeeTaskChange.id)
        )
    ).all()
    stage_titles = {
        stage.id: stage.title
        for stage in (
            await session.scalars(
                select(JourneyStage).where(
                    JourneyStage.id.in_([n.journey_stage_id for n in notices if n.journey_stage_id])
                )
            )
        ).all()
    }
    version_nos = {
        v.id: v.version_no
        for v in (
            await session.scalars(
                select(StageVersion).where(StageVersion.id.in_([n.target_version_id for n in notices]))
            )
        ).all()
    }
    task_ids = [row.employee_task_id for row in rows if row.employee_task_id is not None]
    statuses = (
        {
            task_id: status
            for task_id, status in (
                await session.execute(select(EmployeeTask.id, EmployeeTask.status).where(EmployeeTask.id.in_(task_ids)))
            ).all()
        }
        if task_ids
        else {}
    )
    result: dict[int, NoticeDetail] = {}
    for notice in notices:
        result[notice.id] = NoticeDetail(
            id=notice.id,
            journey_stage_id=notice.journey_stage_id,
            stage_title=stage_titles.get(notice.journey_stage_id or 0, ""),
            version_no=version_nos.get(notice.target_version_id, 0),
            created_at=notice.created_at,
            read_at=notice.read_at,
            new_stage=notice.new_stage,
        )
    for row in rows:
        detail = result[row.notice_id]
        detail.changes.append(
            ChangeDetail(
                id=row.id,
                notice_id=row.notice_id,
                kind=row.kind,
                status=row.status,
                task_title=row.task_title,
                employee_task_id=row.employee_task_id,
                employee_status=statuses.get(row.employee_task_id) if row.employee_task_id else None,
                stage_title=detail.stage_title,
                before=row.before,
                after=None if _is_informational(row) else row.after,
                changed_fields=_fields_of(row),
                informational=_is_informational(row),
            )
        )
    return [result[n.id] for n in notices]


async def mark_read(session: AsyncSession, user: User, notice_id: int) -> None:
    notice = await session.get(JourneyChangeNotice, notice_id)
    if notice is None or notice.user_id != user.id:
        raise PortalError(404, "NOTICE_NOT_FOUND", "portal.notice_not_found")
    if notice.read_at is None:
        notice.read_at = datetime.now(UTC)
        await session.commit()


async def pending_change_by_task(session: AsyncSession, journey_id: int) -> dict[int, int]:
    """`employee_task_id -> change_id` của các thay đổi đang chờ nhân viên xem (để gắn nhãn "Có chỉnh sửa")."""
    rows = (
        await session.execute(
            select(EmployeeTaskChange.employee_task_id, func.max(EmployeeTaskChange.id))
            .join(JourneyChangeNotice, JourneyChangeNotice.id == EmployeeTaskChange.notice_id)
            .where(
                JourneyChangeNotice.employee_journey_id == journey_id,
                EmployeeTaskChange.status == ChangeStatus.PENDING.value,
                EmployeeTaskChange.employee_task_id.is_not(None),
            )
            .group_by(EmployeeTaskChange.employee_task_id)
        )
    ).all()
    return {int(task_id): int(change_id) for task_id, change_id in rows if task_id is not None}


# ───────────────────────────── Cập nhật, giữ bản cũ ─────────────────────────────


async def _load_change(
    session: AsyncSession, user: User, change_id: int
) -> tuple[EmployeeTaskChange, JourneyChangeNotice]:
    change = await session.get(EmployeeTaskChange, change_id)
    notice = await session.get(JourneyChangeNotice, change.notice_id) if change is not None else None
    if change is None or notice is None or notice.user_id != user.id:
        raise PortalError(404, "CHANGE_NOT_FOUND", "portal.change_not_found")
    return change, notice


def _key(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


async def _pending_in_notice(session: AsyncSession, notice_id: int) -> list[EmployeeTaskChange]:
    return list(
        (
            await session.scalars(
                select(EmployeeTaskChange)
                .where(
                    EmployeeTaskChange.notice_id == notice_id, EmployeeTaskChange.status == ChangeStatus.PENDING.value
                )
                .order_by(EmployeeTaskChange.id)
            )
        ).all()
    )


def _closure(change: EmployeeTaskChange, pending: Sequence[EmployeeTaskChange]) -> list[EmployeeTaskChange]:
    """Việc phải cập nhật CÙNG: các việc MỚI mà việc này (và dây chuyền của chúng) cần làm trước."""
    added = {row.origin_key: row for row in pending if row.kind == ChangeKind.ADDED.value}
    chosen: dict[int, EmployeeTaskChange] = {change.id: change}
    queue = [change]
    while queue:
        current = queue.pop()
        for raw in (current.after or {}).get("prerequisite_keys", []):
            row = added.get(_key(raw))
            if row is not None and row.id not in chosen:
                chosen[row.id] = row
                queue.append(row)
    return sorted(chosen.values(), key=lambda row: row.id)


@dataclass
class ChangePreview:
    change_id: int
    kind: str
    keeps_done: bool
    removes_task: bool
    also_update: list[str]
    locked_until: list[str]
    note_done_unchanged: bool


async def preview_change(session: AsyncSession, user: User, change_id: int) -> ChangePreview:
    """Hậu quả cụ thể của nút "Cập nhật" cho một việc (hộp ghi chú trước khi bấm). KHÔNG ghi gì."""
    change, notice = await _load_change(session, user, change_id)
    if change.status != ChangeStatus.PENDING.value:
        raise PortalError(409, "CHANGE_NOT_PENDING", "portal.change_not_pending")
    pending = await _pending_in_notice(session, notice.id)
    closure = _closure(change, pending)
    task = await session.get(EmployeeTask, change.employee_task_id) if change.employee_task_id else None
    done = task is not None and task.status == EmployeeTaskStatus.DONE.value
    unmet: list[str] = []
    after = change.after or {}
    if not done and change.kind != ChangeKind.REMOVED.value:
        journey_tasks = (
            await session.scalars(
                select(EmployeeTask).where(
                    EmployeeTask.employee_journey_id == notice.employee_journey_id, EmployeeTask.deleted_at.is_(None)
                )
            )
        ).all()
        by_key = {t.origin_key: t for t in journey_tasks}
        added_titles = {row.origin_key: row.task_title for row in closure if row.id != change.id}
        titles = list(after.get("prerequisites", []))
        for index, raw in enumerate(after.get("prerequisite_keys", [])):
            key = _key(raw)
            existing = by_key.get(key)
            if existing is not None:
                if existing.status != EmployeeTaskStatus.DONE.value:
                    unmet.append(existing.title)
            elif key in added_titles:
                unmet.append(added_titles[key])
            elif index < len(titles):
                unmet.append(titles[index])
    return ChangePreview(
        change_id=change.id,
        kind=change.kind,
        keeps_done=done,
        removes_task=change.kind == ChangeKind.REMOVED.value and not done,
        also_update=[row.task_title for row in closure if row.id != change.id],
        locked_until=sorted(dict.fromkeys(unmet)),
        note_done_unchanged=done,
    )


async def _recompute_status(session: AsyncSession, task: EmployeeTask) -> None:
    if task.deleted_at is not None or task.status == EmployeeTaskStatus.DONE.value:
        return
    statuses = (
        await session.scalars(
            select(EmployeeTask.status).where(
                EmployeeTask.id.in_(
                    select(EmployeeTaskDependency.depends_on_employee_task_id).where(
                        EmployeeTaskDependency.employee_task_id == task.id
                    )
                ),
                EmployeeTask.deleted_at.is_(None),
            )
        )
    ).all()
    unmet = any(status != EmployeeTaskStatus.DONE.value for status in statuses)
    task.status = EmployeeTaskStatus.LOCKED.value if unmet else EmployeeTaskStatus.READY.value


async def _set_prerequisites(
    session: AsyncSession, journey_id: int, task: EmployeeTask, keys: Sequence[object]
) -> None:
    wanted = {_key(raw) for raw in keys}
    await session.execute(delete(EmployeeTaskDependency).where(EmployeeTaskDependency.employee_task_id == task.id))
    if not wanted:
        return
    targets = (
        await session.scalars(
            select(EmployeeTask).where(
                EmployeeTask.employee_journey_id == journey_id,
                EmployeeTask.deleted_at.is_(None),
                EmployeeTask.origin_key.in_(wanted),
                EmployeeTask.id != task.id,
            )
        )
    ).all()
    for target in targets:
        session.add(EmployeeTaskDependency(employee_task_id=task.id, depends_on_employee_task_id=target.id))


async def _apply(
    session: AsyncSession, notice: JourneyChangeNotice, rows: Sequence[EmployeeTaskChange], *, now: datetime
) -> None:
    journey = await session.get(EmployeeJourney, notice.employee_journey_id)
    assert journey is not None
    # Khóa các việc của lộ trình để phân loại "đã làm hay chưa" không lệch nếu nhân viên vừa bấm hoàn thành.
    await session.scalars(select(EmployeeTask).where(EmployeeTask.employee_journey_id == journey.id).with_for_update())
    stage = await session.get(JourneyStage, notice.journey_stage_id) if notice.journey_stage_id else None
    employee_stage = (
        await _active_stage(session, journey.id, notice.journey_stage_id) if notice.journey_stage_id else None
    )
    touched: list[EmployeeTask] = []
    edges: list[tuple[EmployeeTask, Sequence[object]]] = []
    removed_ids: list[int] = []

    ordered = sorted(
        rows,
        key=lambda r: (
            0 if r.kind == ChangeKind.ADDED.value else 2 if r.kind == ChangeKind.REMOVED.value else 1,
            r.id,
        ),
    )
    for row in ordered:
        after = row.after or {}
        if row.kind == ChangeKind.ADDED.value:
            if employee_stage is None and stage is not None:
                employee_stage = EmployeeStage(
                    employee_journey_id=journey.id,
                    journey_stage_id=stage.id,
                    source_stage_version_id=None,
                    title=stage.title,
                    sort_order=stage.sort_order,
                )
                session.add(employee_stage)
                await session.flush()
            if employee_stage is None:
                continue
            existing = await session.scalar(
                select(EmployeeTask).where(
                    EmployeeTask.employee_journey_id == journey.id,
                    EmployeeTask.origin_key == row.origin_key,
                    EmployeeTask.deleted_at.is_(None),
                )
            )
            if existing is not None:  # đã có (bấm hai lần hoặc cập nhật kèm): không nhân đôi
                row.employee_task_id = existing.id
                continue
            task = EmployeeTask(
                employee_journey_id=journey.id,
                employee_stage_id=employee_stage.id,
                source_task_template_id=after.get("source_task_template_id"),
                origin_key=row.origin_key,
                title=after.get("title", row.task_title),
                body_markdown=after.get("body_markdown", ""),
                required=bool(after.get("required", True)),
                task_group=after.get("task_group"),
                sort_order=int(after.get("sort_order", 0)),
                team_id=journey.team_id,
                status=EmployeeTaskStatus.LOCKED.value,
            )
            session.add(task)
            await session.flush()
            row.employee_task_id = task.id
            touched.append(task)
            edges.append((task, after.get("prerequisite_keys", [])))
        elif row.kind in (ChangeKind.MODIFIED.value, ChangeKind.PREREQUISITES.value):
            task_row = await session.get(EmployeeTask, row.employee_task_id) if row.employee_task_id else None
            if task_row is None or task_row.deleted_at is not None:
                continue
            if row.kind == ChangeKind.MODIFIED.value:
                task_row.title = after.get("title", task_row.title)
                task_row.body_markdown = after.get("body_markdown", task_row.body_markdown)
                task_row.required = bool(after.get("required", task_row.required))
                task_row.task_group = after.get("task_group")
            task_row.sort_order = int(after.get("sort_order", task_row.sort_order))
            if after.get("source_task_template_id") is not None:
                task_row.source_task_template_id = after["source_task_template_id"]
            before_keys = {_key(k) for k in (row.before or {}).get("prerequisite_keys", [])}
            after_keys = {_key(k) for k in after.get("prerequisite_keys", [])}
            if before_keys != after_keys or row.kind == ChangeKind.PREREQUISITES.value:
                edges.append((task_row, after.get("prerequisite_keys", [])))
            touched.append(task_row)
        elif row.kind == ChangeKind.REMOVED.value:
            task_row = await session.get(EmployeeTask, row.employee_task_id) if row.employee_task_id else None
            if task_row is None or task_row.deleted_at is not None:
                continue
            if task_row.status == EmployeeTaskStatus.DONE.value:
                continue  # việc đã làm không bị bỏ
            task_row.deleted_at = now
            removed_ids.append(task_row.id)
    await session.flush()
    for task, keys in edges:
        await _set_prerequisites(session, journey.id, task, keys)
    for task_id in removed_ids:
        dependents = (
            await session.scalars(
                select(EmployeeTask)
                .join(EmployeeTaskDependency, EmployeeTaskDependency.employee_task_id == EmployeeTask.id)
                .where(EmployeeTaskDependency.depends_on_employee_task_id == task_id, EmployeeTask.deleted_at.is_(None))
            )
        ).all()
        await session.execute(
            delete(EmployeeTaskDependency).where(
                (EmployeeTaskDependency.depends_on_employee_task_id == task_id)
                | (EmployeeTaskDependency.employee_task_id == task_id)
            )
        )
        touched.extend(dependents)
    await session.flush()
    for task in touched:
        await _recompute_status(session, task)
    for row in rows:
        row.status = ChangeStatus.ACCEPTED.value
        row.resolved_at = now
    await session.flush()
    siblings = (
        await session.scalars(select(EmployeeTaskChange).where(EmployeeTaskChange.notice_id == notice.id))
    ).all()
    # Còn dòng chờ xem hoặc dòng "giữ bản cũ" (không tính dòng chỉ báo thông tin) thì ngày này chưa theo kịp bản mới.
    remaining = any(
        row.status == ChangeStatus.PENDING.value
        or (row.status == ChangeStatus.DISMISSED.value and not _is_informational(row))
        for row in siblings
    )
    if employee_stage is not None and not remaining:
        employee_stage.source_stage_version_id = notice.target_version_id


async def accept_change(session: AsyncSession, user: User, change_id: int) -> list[int]:
    """Nhân viên bấm "Cập nhật" một việc: thay bằng nội dung mới nhất (kèm các việc liên quan), giữ trạng thái. Trả mã các dòng đã cập nhật."""
    change, notice = await _load_change(session, user, change_id)
    if change.status == ChangeStatus.ACCEPTED.value:
        return [change.id]
    if change.status == ChangeStatus.SUPERSEDED.value:
        raise PortalError(409, "CHANGE_SUPERSEDED", "portal.change_superseded")
    if change.status != ChangeStatus.PENDING.value:
        raise PortalError(409, "CHANGE_NOT_PENDING", "portal.change_not_pending")
    rows = _closure(change, await _pending_in_notice(session, notice.id))
    await _apply(session, notice, rows, now=datetime.now(UTC))
    if notice.read_at is None:
        notice.read_at = datetime.now(UTC)
    await session.commit()
    return [row.id for row in rows]


async def accept_all(session: AsyncSession, user: User, notice_id: int) -> list[int]:
    notice = await session.get(JourneyChangeNotice, notice_id)
    if notice is None or notice.user_id != user.id:
        raise PortalError(404, "NOTICE_NOT_FOUND", "portal.notice_not_found")
    rows = await _pending_in_notice(session, notice.id)
    if rows:
        await _apply(session, notice, rows, now=datetime.now(UTC))
    if notice.read_at is None:
        notice.read_at = datetime.now(UTC)
    await session.commit()
    return [row.id for row in rows]


async def dismiss_change(session: AsyncSession, user: User, change_id: int) -> None:
    change, notice = await _load_change(session, user, change_id)
    if change.status == ChangeStatus.DISMISSED.value:
        return
    if change.status != ChangeStatus.PENDING.value:
        raise PortalError(409, "CHANGE_NOT_PENDING", "portal.change_not_pending")
    change.status = ChangeStatus.DISMISSED.value
    change.resolved_at = datetime.now(UTC)
    if notice.read_at is None:
        notice.read_at = datetime.now(UTC)
    await session.commit()


# ───────────────────────────── HR theo dõi triển khai ─────────────────────────────


@dataclass
class RolloutRow:
    notice_id: int
    user_id: int
    display_name: str
    email: str
    state: str  # UNSEEN | SEEN | UPDATED | KEPT_OLD
    pending: int
    accepted: int
    dismissed: int
    total: int
    read_at: datetime | None


async def rollout_for_version(session: AsyncSession, version: StageVersion) -> list[RolloutRow]:
    notices = (
        await session.execute(
            select(JourneyChangeNotice, User.display_name, User.email)
            .join(User, User.id == JourneyChangeNotice.user_id)
            .where(JourneyChangeNotice.target_version_id == version.id)
            .order_by(User.display_name)
        )
    ).all()
    result: list[RolloutRow] = []
    for notice, name, email in notices:
        counts: dict[str, int] = {}
        for row in (
            await session.scalars(select(EmployeeTaskChange).where(EmployeeTaskChange.notice_id == notice.id))
        ).all():
            if _is_informational(row):
                continue  # dòng chỉ báo thông tin không cần nhân viên làm gì
            if row.kind in {kind.value for kind in AUTO_APPLIED_KINDS} and row.status == ChangeStatus.ACCEPTED.value:
                continue  # thêm/bỏ việc được áp dụng tự động, không phải nhân viên đã bấm "Cập nhật"
            counts[row.status] = counts.get(row.status, 0) + 1
        pending = counts.get(ChangeStatus.PENDING.value, 0)
        accepted = counts.get(ChangeStatus.ACCEPTED.value, 0)
        dismissed = counts.get(ChangeStatus.DISMISSED.value, 0)
        superseded = counts.get(ChangeStatus.SUPERSEDED.value, 0)
        if pending:
            state = "SEEN" if notice.read_at is not None else "UNSEEN"
        elif accepted:
            state = "UPDATED"
        elif dismissed:
            state = "KEPT_OLD"
        else:
            state = "SUPERSEDED" if superseded else "UPDATED"
        result.append(
            RolloutRow(
                notice_id=notice.id,
                user_id=notice.user_id,
                display_name=name,
                email=email,
                state=state,
                pending=pending,
                accepted=accepted,
                dismissed=dismissed,
                total=pending + accepted + dismissed + superseded,
                read_at=notice.read_at,
            )
        )
    return result
