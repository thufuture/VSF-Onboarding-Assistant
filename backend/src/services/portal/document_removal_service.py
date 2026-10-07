"""Tắt hoặc xóa một tài liệu khi đang có task trích dẫn nó.

Task của HR trích dẫn tài liệu qua `task_source_mappings` (khóa ngoại RESTRICT tới tài liệu), nên không thể xóa tài liệu mà bỏ mặc
các task. Người dùng chọn một trong hai:

- `KEEP`: giữ mọi task đã tạo. Tắt tài liệu thì task giữ nguyên cả nguồn trích dẫn; xóa tài liệu thì task vẫn còn nhưng mất nguồn
  trích dẫn từ tài liệu này (không còn gì để trích).
- `DELETE`: xóa các task **chỉ** dựa vào tài liệu này. Task còn trích dẫn tài liệu khác không bị xóa (chỉ mất nguồn từ tài liệu này
  nếu xóa tài liệu), vì nó vẫn có căn cứ ở chỗ khác.

Nhân viên đã nhận bản sao riêng của task (`employee_tasks`) nên không bao giờ bị xóa theo: chỉ gỡ liên kết truy nguồn
(`source_task_template_id` về NULL). Xóa tài liệu là xóa cứng, không hoàn tác: mọi phiên bản, mục, đoạn đã nhúng và liên kết nguồn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_version import DocumentVersion
from src.model.employee_task import EmployeeTask
from src.model.enums import DocumentStatus, VersionStatus
from src.model.journey_stage import JourneyStage
from src.model.stage_version import StageVersion
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.ingest.version_lifecycle import delete_sections_and_chunks
from src.services.portal.errors import PortalError

TaskChoice = Literal["KEEP", "DELETE"]


@dataclass(frozen=True)
class TaskRef:
    id: int
    title: str
    day_title: str
    version_status: str


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
            select(TaskTemplate.id, TaskTemplate.title, JourneyStage.title, StageVersion.status)
            .join(StageVersion, StageVersion.id == TaskTemplate.stage_version_id)
            .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
            .where(
                TaskTemplate.id.in_(
                    select(TaskSourceMapping.task_template_id).where(TaskSourceMapping.document_id == document_id)
                )
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
    for task_id, title, day_title, version_status in rows:
        ref = TaskRef(id=int(task_id), title=title, day_title=day_title, version_status=str(version_status))
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


async def _delete_tasks(session: AsyncSession, task_ids: list[int]) -> int:
    """Xóa task (kéo theo tiên quyết và nguồn trích dẫn của chúng). Bản sao của nhân viên được giữ, chỉ gỡ liên kết truy nguồn."""
    if not task_ids:
        return 0
    await session.execute(
        update(EmployeeTask)
        .where(EmployeeTask.source_task_template_id.in_(task_ids))
        .values(source_task_template_id=None)
    )
    await session.execute(delete(TaskTemplate).where(TaskTemplate.id.in_(task_ids)))
    return len(task_ids)


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
) -> Document:
    """Tắt hoặc bật lại tài liệu. Chỉ khi tắt mới xét `tasks`: `DELETE` xóa các task chỉ dựa vào tài liệu này, còn lại giữ nguyên."""
    document = await _require_document(session, document_id)
    previous = document.status
    deleted = 0
    if status == DocumentStatus.ARCHIVED and tasks == "DELETE":
        impact = await document_impact(session, document_id)
        deleted = await _delete_tasks(session, [ref.id for ref in impact.only_tasks])
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
    return document


async def delete_document(session: AsyncSession, *, document_id: int, tasks: TaskChoice | None, actor: User) -> None:
    """Xóa cứng tài liệu cùng mọi phiên bản. Có task trích dẫn thì BẮT BUỘC chọn `tasks` (giữ hoặc xóa), không tự quyết thay người dùng."""
    document = await _require_document(session, document_id)
    impact = await document_impact(session, document_id)
    if impact.processing:
        raise PortalError(409, "DOCUMENT_PROCESSING", "portal.document_processing")
    has_tasks = bool(impact.only_tasks or impact.shared_tasks)
    if has_tasks and tasks is None:
        raise PortalError(409, "TASK_CHOICE_REQUIRED", "portal.task_choice_required")

    deleted = 0
    if tasks == "DELETE":
        deleted = await _delete_tasks(session, [ref.id for ref in impact.only_tasks])
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
