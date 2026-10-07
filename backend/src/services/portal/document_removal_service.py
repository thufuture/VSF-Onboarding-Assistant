"""Tắt hoặc xóa một tài liệu khi đang có task trích dẫn nó.

Task của HR trích dẫn tài liệu qua `task_source_mappings` (khóa ngoại RESTRICT tới tài liệu), nên không thể xóa tài liệu mà bỏ mặc
các task. Người dùng chọn một trong hai:

- `KEEP`: giữ mọi task đã tạo. Tắt tài liệu thì task giữ nguyên cả nguồn trích dẫn; xóa tài liệu thì task vẫn còn nhưng mất nguồn
  trích dẫn từ tài liệu này (không còn gì để trích).
- `DELETE`: xóa các task **chỉ** dựa vào tài liệu này. Task còn trích dẫn tài liệu khác không bị xóa (chỉ mất nguồn từ tài liệu này
  nếu xóa tài liệu), vì nó vẫn có căn cứ ở chỗ khác.

Chỉ xét task ở bản nháp và bản ĐANG ÁP DỤNG của một ngày (bản lưu trữ là lịch sử, không đụng). Task ở bản đang áp dụng KHÔNG bị xóa
thẳng: việc xóa được ghi vào BẢN NHÁP của ngày đó (tạo từ bản đang áp dụng nếu chưa có). HR xem rồi bấm "Cập nhật cho nhân viên" thì
mới áp dụng và mỗi nhân viên nhận đúng MỘT thông báo (xem `rollout_service`); không áp dụng thì lộ trình của ai cũng không đổi.

Xóa tài liệu là xóa cứng, không hoàn tác: mọi phiên bản, mục, đoạn đã nhúng và liên kết nguồn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_version import DocumentVersion
from src.model.employee_task import EmployeeTask
from src.model.enums import DocumentStatus, StageVersionStatus, VersionStatus
from src.model.journey_stage import JourneyStage
from src.model.stage_version import StageVersion
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.ingest.version_lifecycle import delete_sections_and_chunks
from src.services.portal import stage_version_service
from src.services.portal.errors import PortalError

TaskChoice = Literal["KEEP", "DELETE"]


@dataclass(frozen=True)
class TaskRef:
    id: int
    title: str
    day_title: str
    version_status: str
    origin_key: UUID
    stage_id: int


@dataclass(frozen=True)
class StageDraftChange:
    """Một ngày đã được ghi việc xóa task vào bản nháp (chưa áp dụng cho nhân viên)."""

    stage_id: int
    stage_title: str
    version_id: int
    version_no: int
    removed_tasks: int


@dataclass(frozen=True)
class DocumentImpact:
    only_tasks: list[TaskRef]  # chỉ trích dẫn tài liệu này
    shared_tasks: list[TaskRef]  # còn trích dẫn tài liệu khác
    employee_copies: int  # bản sao đã giao cho nhân viên từ các task "chỉ từ tài liệu này"
    version_count: int
    processing: bool  # đang có phiên bản được xử lý nền


async def _require_document(session: AsyncSession, document_id: int) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise PortalError(404, "DOCUMENT_NOT_FOUND", "portal.document_not_found")
    return document


async def document_impact(session: AsyncSession, document_id: int) -> DocumentImpact:
    await _require_document(session, document_id)
    rows = (
        await session.execute(
            select(
                TaskTemplate.id,
                TaskTemplate.title,
                JourneyStage.title,
                StageVersion.status,
                TaskTemplate.origin_key,
                TaskTemplate.journey_stage_id,
            )
            .join(StageVersion, StageVersion.id == TaskTemplate.stage_version_id)
            .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
            .where(
                StageVersion.status.in_([StageVersionStatus.DRAFT.value, StageVersionStatus.APPLIED.value]),
                TaskTemplate.id.in_(
                    select(TaskSourceMapping.task_template_id).where(TaskSourceMapping.document_id == document_id)
                ),
            )
            .order_by(JourneyStage.sort_order, TaskTemplate.sort_order, TaskTemplate.id)
        )
    ).all()
    ids = [int(row[0]) for row in rows]
    cited_elsewhere: set[int] = set()
    if ids:
        cited_elsewhere = set(
            (
                await session.scalars(
                    select(TaskSourceMapping.task_template_id)
                    .where(TaskSourceMapping.task_template_id.in_(ids), TaskSourceMapping.document_id != document_id)
                    .distinct()
                )
            ).all()
        )
    only: list[TaskRef] = []
    shared: list[TaskRef] = []
    for task_id, title, day_title, version_status, origin_key, stage_id in rows:
        ref = TaskRef(
            id=int(task_id),
            title=title,
            day_title=day_title,
            version_status=str(version_status),
            origin_key=origin_key,
            stage_id=int(stage_id),
        )
        (shared if ref.id in cited_elsewhere else only).append(ref)
    copies = 0
    if only:
        copies = int(
            await session.scalar(
                select(func.count())
                .select_from(EmployeeTask)
                .where(EmployeeTask.source_task_template_id.in_([ref.id for ref in only]))
            )
            or 0
        )
    version_count = int(
        await session.scalar(
            select(func.count()).select_from(DocumentVersion).where(DocumentVersion.document_id == document_id)
        )
        or 0
    )
    processing = (
        await session.scalar(
            select(func.count())
            .select_from(DocumentVersion)
            .where(DocumentVersion.document_id == document_id, DocumentVersion.status == VersionStatus.PROCESSING)
        )
        or 0
    ) > 0
    return DocumentImpact(
        only_tasks=only, shared_tasks=shared, employee_copies=copies, version_count=version_count, processing=processing
    )


async def _delete_tasks(session: AsyncSession, refs: list[TaskRef], actor: User) -> list[StageDraftChange]:
    """Ghi việc xóa task vào BẢN NHÁP của từng ngày. Bản đang áp dụng và lộ trình của nhân viên không đổi cho tới khi HR áp dụng.

    Task đã nằm ở bản nháp thì xóa thẳng ở đó (chưa ai thấy); task ở bản đang áp dụng thì xóa bản sao cùng `origin_key` trong
    bản nháp làm việc của ngày (tạo từ bản đang áp dụng nếu chưa có).
    """
    changes: list[StageDraftChange] = []
    for stage_id in dict.fromkeys(ref.stage_id for ref in refs):
        stage_refs = [ref for ref in refs if ref.stage_id == stage_id]
        stage = await session.get(JourneyStage, stage_id)
        if stage is None:
            continue
        live = [ref for ref in stage_refs if ref.version_status == StageVersionStatus.APPLIED.value]
        draft = await stage_version_service.working_draft(session, stage, actor) if live else None
        if draft is not None:
            await session.execute(
                delete(TaskTemplate).where(
                    TaskTemplate.stage_version_id == draft.id,
                    TaskTemplate.origin_key.in_([ref.origin_key for ref in live]),
                )
            )
        draft_ids = [ref.id for ref in stage_refs if ref.version_status == StageVersionStatus.DRAFT.value]
        if draft_ids:
            await session.execute(delete(TaskTemplate).where(TaskTemplate.id.in_(draft_ids)))
        if draft is None:
            continue
        changes.append(
            StageDraftChange(
                stage_id=stage.id,
                stage_title=stage.title,
                version_id=draft.id,
                version_no=draft.version_no,
                removed_tasks=len({ref.origin_key for ref in stage_refs}),
            )
        )
    return changes


def _audit(actor: User, action: str, document_id: int, before: dict[str, object], after: dict[str, object]) -> AuditLog:
    return AuditLog(
        actor_id=actor.id, action=action, entity_type="document", entity_id=str(document_id), before=before, after=after
    )


async def set_status(
    session: AsyncSession,
    *,
    document_id: int,
    status: DocumentStatus,
    tasks: TaskChoice | None,
    actor: User,
) -> tuple[Document, list[StageDraftChange]]:
    """Tắt hoặc bật lại tài liệu. Chỉ khi tắt mới xét `tasks`: `DELETE` ghi việc xóa các task chỉ dựa vào tài liệu này vào bản nháp."""
    document = await _require_document(session, document_id)
    previous = document.status
    drafts: list[StageDraftChange] = []
    deleted = 0
    if status == DocumentStatus.ARCHIVED and tasks == "DELETE":
        impact = await document_impact(session, document_id)
        deleted = len(impact.only_tasks)
        drafts = await _delete_tasks(session, impact.only_tasks, actor)
    document.status = status.value
    action = "ARCHIVE_DOCUMENT" if status == DocumentStatus.ARCHIVED else "REACTIVATE_DOCUMENT"
    session.add(
        _audit(
            actor,
            action,
            document_id,
            {"status": previous},
            {"status": status.value, "tasks": tasks, "tasks_deleted": deleted},
        )
    )
    await session.commit()
    return document, drafts


async def delete_document(
    session: AsyncSession, *, document_id: int, tasks: TaskChoice | None, actor: User
) -> list[StageDraftChange]:
    """Xóa cứng tài liệu cùng mọi phiên bản. Có task trích dẫn thì BẮT BUỘC chọn `tasks` (giữ hoặc xóa), không tự quyết thay người dùng."""
    document = await _require_document(session, document_id)
    impact = await document_impact(session, document_id)
    if impact.processing:
        raise PortalError(409, "DOCUMENT_PROCESSING", "portal.document_processing")
    has_tasks = bool(impact.only_tasks or impact.shared_tasks)
    if has_tasks and tasks is None:
        raise PortalError(409, "TASK_CHOICE_REQUIRED", "portal.task_choice_required")

    drafts: list[StageDraftChange] = []
    deleted = 0
    if tasks == "DELETE":
        deleted = len(impact.only_tasks)
        drafts = await _delete_tasks(session, impact.only_tasks, actor)
    # Task còn lại (giữ, hoặc còn nguồn ở tài liệu khác) mất nguồn trích dẫn từ tài liệu này; khóa ngoại RESTRICT buộc phải gỡ trước.
    await session.execute(delete(TaskSourceMapping).where(TaskSourceMapping.document_id == document_id))
    version_ids = list(
        (await session.scalars(select(DocumentVersion.id).where(DocumentVersion.document_id == document_id))).all()
    )
    for version_id in version_ids:
        await delete_sections_and_chunks(session, version_id)
    await session.execute(delete(DocumentVersion).where(DocumentVersion.document_id == document_id))
    session.add(
        _audit(
            actor,
            "DELETE_DOCUMENT",
            document_id,
            {"title": document.title, "source_key": document.source_key, "versions": len(version_ids)},
            {
                "tasks": tasks,
                "tasks_deleted": deleted,
                "tasks_kept": len(impact.only_tasks) + len(impact.shared_tasks) - deleted,
            },
        )
    )
    await session.execute(delete(Document).where(Document.id == document_id))
    await session.commit()
    return drafts
