"""Phiên bản của từng ngày trong Quản lý task: tạo bản nháp, sửa chỉ khi nháp, áp dụng, xóa nháp.

Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md (mục 4.2, 4.3).
- Mỗi ngày có tối đa MỘT bản `APPLIED` (index duy nhất từng phần); bản `APPLIED` và `ARCHIVED` bất biến.
- Áp dụng KHÔNG đổi lộ trình của nhân viên đã có: chỉ ghi thông báo (`rollout_service`).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.audit_log import AuditLog
from src.model.enums import JourneyTemplateStatus, StageVersionStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.stage_version import StageVersion
from src.model.task_dependency import TaskDependency
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.portal import rollout_service
from src.services.portal.errors import PortalError


def _not_editable() -> PortalError:
    return PortalError(409, "VERSION_NOT_EDITABLE", "portal.version_not_editable")


async def get_version(session: AsyncSession, version_id: int) -> StageVersion:
    version = await session.get(StageVersion, version_id)
    if version is None:
        raise PortalError(404, "STAGE_VERSION_NOT_FOUND", "portal.stage_version_not_found")
    return version


async def get_stage(session: AsyncSession, stage_id: int) -> JourneyStage:
    stage = await session.get(JourneyStage, stage_id)
    if stage is None:
        raise PortalError(404, "STAGE_NOT_FOUND", "portal.stage_not_found")
    return stage


async def get_template_of(session: AsyncSession, version: StageVersion) -> JourneyTemplate:
    stage = await get_stage(session, version.journey_stage_id)
    template = await session.get(JourneyTemplate, stage.journey_template_id)
    if template is None:
        raise PortalError(404, "JOURNEY_TEMPLATE_NOT_FOUND", "portal.journey_template_not_found")
    return template


def ensure_editable(version: StageVersion) -> None:
    """Chỉ bản nháp sửa được: sửa bản đang áp dụng hay đã lưu trữ sẽ đổi lộ trình mà không ai biết (lỗ hổng đã vá)."""
    if version.status != StageVersionStatus.DRAFT:
        raise _not_editable()


async def versions_of_stage(session: AsyncSession, stage_id: int) -> list[StageVersion]:
    rows = await session.scalars(
        select(StageVersion).where(StageVersion.journey_stage_id == stage_id).order_by(StageVersion.version_no)
    )
    return list(rows.all())


def pick_default(versions: Iterable[StageVersion]) -> StageVersion | None:
    """Bản hiển thị mặc định của một ngày: đang áp dụng, nếu chưa có thì bản nháp mới nhất, nếu không nữa thì bản mới nhất."""
    ordered = sorted(versions, key=lambda v: v.version_no)
    applied = next((v for v in ordered if v.status == StageVersionStatus.APPLIED), None)
    if applied is not None:
        return applied
    drafts = [v for v in ordered if v.status == StageVersionStatus.DRAFT]
    if drafts:
        return drafts[-1]
    return ordered[-1] if ordered else None


async def default_versions(session: AsyncSession, stage_ids: Iterable[int]) -> dict[int, StageVersion]:
    ids = sorted(set(stage_ids))
    if not ids:
        return {}
    rows = (await session.scalars(select(StageVersion).where(StageVersion.journey_stage_id.in_(ids)))).all()
    grouped: dict[int, list[StageVersion]] = {}
    for version in rows:
        grouped.setdefault(version.journey_stage_id, []).append(version)
    result: dict[int, StageVersion] = {}
    for stage_id, versions in grouped.items():
        picked = pick_default(versions)
        if picked is not None:
            result[stage_id] = picked
    return result


async def create_initial_version(session: AsyncSession, stage: JourneyStage, user: User | None) -> StageVersion:
    """Ngày mới tạo có sẵn v1 (nháp) để nhận task."""
    version = StageVersion(
        journey_stage_id=stage.id,
        version_no=1,
        status=StageVersionStatus.DRAFT.value,
        created_by=user.id if user else None,
    )
    session.add(version)
    await session.flush()
    return version


async def _next_version_no(session: AsyncSession, stage_id: int) -> int:
    current = await session.scalar(
        select(func.max(StageVersion.version_no)).where(StageVersion.journey_stage_id == stage_id)
    )
    return int(current or 0) + 1


async def _clone_tasks(session: AsyncSession, source: StageVersion, target: StageVersion) -> None:
    """Sao chép task, tiên quyết và nguồn trích dẫn sang bản `target`; `origin_key` được giữ nguyên."""
    tasks = (
        await session.scalars(
            select(TaskTemplate).where(TaskTemplate.stage_version_id == source.id).order_by(TaskTemplate.sort_order)
        )
    ).all()
    id_map: dict[int, int] = {}
    for task in tasks:
        copy = TaskTemplate(
            journey_stage_id=target.journey_stage_id,
            stage_version_id=target.id,
            origin_key=task.origin_key,
            title=task.title,
            body_markdown=task.body_markdown,
            sort_order=task.sort_order,
            required=task.required,
            task_group=task.task_group,
            team_id=task.team_id,
        )
        session.add(copy)
        await session.flush()
        id_map[task.id] = copy.id
    if not id_map:
        return
    dependencies = (
        await session.scalars(select(TaskDependency).where(TaskDependency.task_template_id.in_(list(id_map))))
    ).all()
    for edge in dependencies:
        if edge.depends_on_task_template_id in id_map:
            session.add(
                TaskDependency(
                    task_template_id=id_map[edge.task_template_id],
                    depends_on_task_template_id=id_map[edge.depends_on_task_template_id],
                )
            )
    mappings = (
        await session.scalars(select(TaskSourceMapping).where(TaskSourceMapping.task_template_id.in_(list(id_map))))
    ).all()
    for mapping in mappings:
        session.add(
            TaskSourceMapping(
                task_template_id=id_map[mapping.task_template_id],
                document_id=mapping.document_id,
                document_version_id=mapping.document_version_id,
                document_section_id=mapping.document_section_id,
                quote=mapping.quote,
            )
        )


async def create_draft(
    session: AsyncSession,
    *,
    stage: JourneyStage,
    from_version_id: int | None,
    note: str | None,
    user: User,
    commit: bool = True,
    empty: bool = False,
) -> StageVersion:
    """Tạo bản nháp mới của một ngày, sao chép từ `from_version_id` (mặc định: bản đang áp dụng, không thì bản mới nhất).

    `empty=True`: bản nháp RỖNG (không sao chép task nào), dùng khi thay cả ngày bằng một roadmap mới (ví dụ vừa tạo bằng AI)."""
    versions = await versions_of_stage(session, stage.id)
    source: StageVersion | None
    if from_version_id is not None:
        source = next((v for v in versions if v.id == from_version_id), None)
        if source is None:
            raise PortalError(404, "STAGE_VERSION_NOT_FOUND", "portal.stage_version_not_found")
    else:
        source = pick_default([v for v in versions if v.status != StageVersionStatus.DRAFT]) or pick_default(versions)
    draft = StageVersion(
        journey_stage_id=stage.id,
        version_no=await _next_version_no(session, stage.id),
        status=StageVersionStatus.DRAFT.value,
        note=note.strip() if note and note.strip() else None,
        based_on_version_id=source.id if source else None,
        created_by=user.id,
    )
    session.add(draft)
    await session.flush()
    if source is not None and not empty:
        await _clone_tasks(session, source, draft)
    if commit:
        await session.commit()
    return draft


async def working_draft(session: AsyncSession, stage: JourneyStage, user: User) -> StageVersion:
    """Bản nháp để ghi task vào (cách cũ `POST /stages/{id}/tasks` và AI): nháp mới nhất; chưa có thì tạo từ bản đang áp dụng."""
    versions = await versions_of_stage(session, stage.id)
    drafts = [v for v in versions if v.status == StageVersionStatus.DRAFT]
    if drafts:
        return drafts[-1]
    return await create_draft(session, stage=stage, from_version_id=None, note=None, user=user, commit=False)


async def update_note(session: AsyncSession, version: StageVersion, note: str | None) -> StageVersion:
    version.note = note.strip() if note and note.strip() else None
    await session.commit()
    return version


async def delete_draft(session: AsyncSession, version: StageVersion) -> None:
    ensure_editable(version)
    count = await session.scalar(
        select(func.count(StageVersion.id)).where(StageVersion.journey_stage_id == version.journey_stage_id)
    )
    if (count or 0) <= 1:
        raise PortalError(409, "LAST_VERSION", "portal.last_version")
    await session.execute(delete(StageVersion).where(StageVersion.id == version.id))
    await session.commit()


@dataclass
class ApplyResult:
    version: StageVersion
    notified_count: int


async def apply_version(session: AsyncSession, *, version: StageVersion, user: User) -> ApplyResult:
    """Áp dụng một bản nháp: bản đang áp dụng chuyển `ARCHIVED`, bản này thành `APPLIED`, rồi ghi thông báo cho nhân viên.

    Làm trong MỘT transaction. Lộ trình của nhân viên đã có KHÔNG bị đổi.
    """
    if version.status != StageVersionStatus.DRAFT:
        raise PortalError(409, "VERSION_NOT_DRAFT", "portal.version_not_draft")
    task_count = await session.scalar(
        select(func.count(TaskTemplate.id)).where(TaskTemplate.stage_version_id == version.id)
    )
    if not task_count:
        raise PortalError(409, "VERSION_EMPTY", "portal.version_empty")
    # Khóa dòng ngày để hai lần áp dụng cùng lúc không lọt qua index duy nhất.
    stage = (
        await session.scalars(select(JourneyStage).where(JourneyStage.id == version.journey_stage_id).with_for_update())
    ).one()
    current = (
        await session.scalars(
            select(StageVersion).where(
                StageVersion.journey_stage_id == stage.id, StageVersion.status == StageVersionStatus.APPLIED
            )
        )
    ).all()
    for old in current:
        old.status = StageVersionStatus.ARCHIVED.value
    await session.flush()
    now = datetime.now(UTC)
    version.status = StageVersionStatus.APPLIED.value
    version.applied_at = now
    version.applied_by = user.id
    template = await session.get(JourneyTemplate, stage.journey_template_id)
    if template is not None and template.status != JourneyTemplateStatus.PUBLISHED:
        template.status = JourneyTemplateStatus.PUBLISHED.value
        template.published_at = now
    await session.flush()
    notified = await rollout_service.create_notices(session, version=version, applied_by=user.id)
    session.add(
        AuditLog(
            actor_id=user.id,
            action="APPLY_STAGE_VERSION",
            entity_type="stage_version",
            entity_id=str(version.id),
            after={"stage": stage.title, "version_no": version.version_no, "notified": notified},
        )
    )
    await session.commit()
    return ApplyResult(version=version, notified_count=notified)
