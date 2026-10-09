"""Quản lý tài liệu theo phiên bản: tải thành bản nháp, sao chép, sửa nháp, xóa nháp, kích hoạt.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 16 (và quyết định 4, 5 ở mục 0.1).

Nguyên tắc: bản đang áp dụng và bản đã thay thế **không sửa tại chỗ**. Muốn sửa nội dung thì sao chép thành bản nháp
mới (từ bất kỳ bản nào), sửa trên nháp rồi kích hoạt. Nháp không tốn tiền embedding và Viga không thấy.
"""

from __future__ import annotations

import asyncio
import mimetypes
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import (
    Confidentiality,
    ContentKind,
    DocumentStatus,
    JobKind,
    VersionSource,
    VersionStatus,
)
from src.model.job import Job
from src.model.task_source_mapping import TaskSourceMapping
from src.model.user import User
from src.services.ingest.parser import MIN_TEXT_LENGTH, ParseError, parse_document
from src.services.ingest.storage import StoragePort
from src.services.ingest.structure import analyze_structure
from src.services.ingest.version_lifecycle import DisplayState, checksum_of, display_state
from src.services.portal import word_editor
from src.services.portal.errors import PortalError
from src.services.portal.job_service import enqueue_job

LABEL_MAX_LENGTH = 32
# Chưa biết model embedding thật cho tới khi kích hoạt (bản nháp không embedding); cột này bắt buộc nên ghi tạm.
PENDING_EMBEDDING_MODEL = "pending"
ACTIVATABLE_STATUSES = (VersionStatus.DRAFT, VersionStatus.ARCHIVED, VersionStatus.ACTIVE)


@dataclass(frozen=True)
class DraftResult:
    document_id: int
    version_id: int
    created_document: bool
    reused: bool  # True: đã có bản cùng nhãn, cùng nội dung (idempotent), không tạo mới
    structure_quality: str | None = None
    structure_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class VersionItem:
    id: int
    version_label: str
    revision_no: int
    state: DisplayState
    status: str
    effective_from: date | None
    effective_to: date | None
    source: str
    parent_version_id: int | None
    original_filename: str
    uploaded_by_name: str | None
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None
    failure_reason: str | None
    section_count: int
    task_count: int
    structure_quality: str | None = None
    structure_warnings: tuple[str, ...] = ()
    ai_split: str | None = None  # None | APPLIED | SKIPPED


@dataclass(frozen=True)
class VersionDetail:
    item: VersionItem
    document_id: int
    document_title: str
    markdown: str
    can_edit: bool


def _clean_label(label: str) -> str:
    label = " ".join(label.split())
    if not label:
        raise PortalError(422, "VERSION_LABEL_REQUIRED", "portal.version_label_required")
    if len(label) > LABEL_MAX_LENGTH:
        raise PortalError(422, "VERSION_LABEL_TOO_LONG", "portal.version_label_too_long")
    return label


def _check_markdown(markdown: str) -> str:
    text = markdown.strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise PortalError(422, "VERSION_CONTENT_TOO_SHORT", "portal.version_content_too_short")
    return markdown


async def _require_document(session: AsyncSession, document_id: int) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise PortalError(404, "DOCUMENT_NOT_FOUND", "portal.document_not_found")
    return document


async def _require_version(session: AsyncSession, document_id: int, version_id: int) -> DocumentVersion:
    version = await session.get(DocumentVersion, version_id)
    if version is None or version.document_id != document_id:
        raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
    return version


async def _label_taken(session: AsyncSession, document_id: int, label: str, *, except_id: int | None = None) -> bool:
    query = select(DocumentVersion.id).where(
        DocumentVersion.document_id == document_id, DocumentVersion.version_label == label
    )
    if except_id is not None:
        query = query.where(DocumentVersion.id != except_id)
    return (await session.scalar(query)) is not None


async def _next_revision_no(session: AsyncSession, document_id: int) -> int:
    current = await session.scalar(
        select(func.max(DocumentVersion.revision_no)).where(DocumentVersion.document_id == document_id)
    )
    return int(current or 0) + 1


async def _unique_label(session: AsyncSession, document_id: int, base: str) -> str:
    """Nhãn gợi ý không trùng: thêm " 2", " 3"... và cắt cho vừa `LABEL_MAX_LENGTH`."""
    candidate = base[:LABEL_MAX_LENGTH]
    counter = 2
    while await _label_taken(session, document_id, candidate):
        suffix = f" {counter}"
        candidate = base[: LABEL_MAX_LENGTH - len(suffix)] + suffix
        counter += 1
    return candidate


def _audit(actor: User, action: str, version: DocumentVersion, **extra: object) -> AuditLog:
    return AuditLog(
        actor_id=actor.id,
        action=action,
        entity_type="document_version",
        entity_id=str(version.id),
        after={"document_id": version.document_id, "version_label": version.version_label, **extra},
    )


async def create_draft_from_upload(
    session: AsyncSession,
    *,
    content: bytes,
    filename: str,
    actor: User,
    storage: StoragePort,
    version_label: str,
    effective_from: date | None,
    document_id: int | None = None,
    title: str | None = None,
    category_slug: str | None = None,
    source_key: str | None = None,
) -> DraftResult:
    """Đọc file (markitdown), lưu file gốc, tạo **bản nháp**. Nhanh, không embedding (mục 16.3)."""
    label = _clean_label(version_label)
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        # markitdown chạy đồng bộ và nặng CPU: đưa ra luồng riêng để không chặn các request khác.
        parsed = await asyncio.to_thread(parse_document, tmp_path)
    except ParseError as exc:
        raise PortalError(422, "INGEST_FAILED", "portal.ingest_failed") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    created_document = False
    if document_id is not None:
        document = await _require_document(session, document_id)
    else:
        if not (title and category_slug and source_key):
            raise PortalError(422, "DOCUMENT_FIELDS_REQUIRED", "portal.document_fields_required")
        found = await session.scalar(select(Document).where(Document.source_key == source_key))
        if found is not None:
            document = found
        else:
            category = await session.scalar(select(DocumentCategory).where(DocumentCategory.slug == category_slug))
            if category is None:
                raise PortalError(422, "CATEGORY_NOT_FOUND", "portal.category_not_found")
            document = Document(
                title=title,
                category_id=category.id,
                owner_id=actor.id,
                content_kind=ContentKind.GENERAL.value,
                confidentiality=Confidentiality.INTERNAL.value,
                source_key=source_key,
            )
            session.add(document)
            await session.flush()
            created_document = True

    existing = await session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id, DocumentVersion.version_label == label
        )
    )
    if existing is not None:
        if existing.content_checksum == parsed.content_checksum:
            report = existing.quality_report.get("structure") or {}
            return DraftResult(
                document.id,
                existing.id,
                created_document=False,
                reused=True,
                structure_quality=report.get("quality"),
                structure_warnings=tuple(report.get("warnings", ())),
            )
        raise PortalError(409, "VERSION_LABEL_EXISTS", "portal.version_label_exists")

    try:
        # Tên file theo checksum của FILE, nên hai file khác byte không ghi đè nhau trên Cloudinary.
        storage_key = await storage.store(content, checksum=parsed.file_checksum, filename=filename)
    except Exception as exc:
        raise PortalError(502, "STORAGE_FAILED", "portal.storage_failed") from exc

    # Bậc 2 và 3 (mục 13): thăng tiêu đề giả nếu file không có heading thật và đo chất lượng cấu trúc. Bản nháp lưu
    # Markdown đã có heading để HR thấy và sửa được trước khi kích hoạt.
    structured_markdown, structure = analyze_structure(parsed.markdown)
    version = DocumentVersion(
        document_id=document.id,
        version_label=label,
        revision_no=await _next_revision_no(session, document.id),
        status=VersionStatus.DRAFT.value,
        original_filename=filename,
        mime_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
        size_bytes=parsed.size_bytes,
        storage_key=storage_key,
        file_checksum=parsed.file_checksum,
        content_checksum=parsed.content_checksum,
        parser="markitdown",
        markdown=structured_markdown,
        quality_report={"has_embedded_images": parsed.has_embedded_images, "structure": structure.as_dict()},
        effective_from=effective_from,
        embedding_model_version=PENDING_EMBEDDING_MODEL,
        source=VersionSource.UPLOAD.value,
        uploaded_by=actor.id,
        updated_by=actor.id,
    )
    session.add(version)
    await session.flush()
    session.add(_audit(actor, "CREATE_DRAFT", version, source="UPLOAD"))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PortalError(409, "VERSION_LABEL_EXISTS", "portal.version_label_exists") from exc
    return DraftResult(
        document.id,
        version.id,
        created_document=created_document,
        reused=False,
        structure_quality=structure.quality,
        structure_warnings=tuple(structure.warnings),
    )


def _copied_report(source: DocumentVersion) -> dict[str, Any]:
    """Báo cáo của bản sao; ghi nhớ file .docx dùng chung còn khớp nội dung để trình soạn thảo Word mở đúng file gốc."""
    report = {
        k: v
        for k, v in source.quality_report.items()
        if k not in (word_editor.DOCX_CHECKSUM_KEY, word_editor.WORKING_DOCX_KEY, word_editor.PENDING_SAVE_KEY)
    }
    working = word_editor.working_docx_for_copy(source)
    if working is not None:
        report[word_editor.WORKING_DOCX_KEY] = working
    return report


async def copy_version(
    session: AsyncSession, *, document_id: int, version_id: int, actor: User, label: str | None
) -> DocumentVersion:
    """Sao chép một phiên bản (bất kỳ trạng thái nào) thành bản nháp mới; file gốc trỏ về bản nguồn."""
    source = await _require_version(session, document_id, version_id)
    if label is not None and label.strip():
        new_label = _clean_label(label)
        if await _label_taken(session, document_id, new_label):
            raise PortalError(409, "VERSION_LABEL_EXISTS", "portal.version_label_exists")
    else:
        new_label = await _unique_label(session, document_id, f"{source.version_label} (sao chép)")

    draft = DocumentVersion(
        document_id=document_id,
        version_label=new_label,
        revision_no=await _next_revision_no(session, document_id),
        status=VersionStatus.DRAFT.value,
        original_filename=source.original_filename,
        mime_type=source.mime_type,
        size_bytes=source.size_bytes,
        storage_key=source.storage_key,  # không tải lại file: dùng chung file gốc của bản nguồn
        file_checksum=source.file_checksum,
        content_checksum=source.content_checksum,
        page_count=source.page_count,
        parser=source.parser,
        markdown=source.markdown,
        quality_report=_copied_report(source),
        effective_from=None,
        embedding_model_version=PENDING_EMBEDDING_MODEL,
        parent_version_id=source.id,
        source=VersionSource.EDITED.value,
        uploaded_by=actor.id,
        updated_by=actor.id,
    )
    session.add(draft)
    await session.flush()
    session.add(_audit(actor, "CREATE_DRAFT", draft, source="COPY", parent_version_id=source.id))
    await session.commit()
    return draft


async def update_draft(
    session: AsyncSession,
    *,
    document_id: int,
    version_id: int,
    actor: User,
    expected_updated_at: datetime,
    markdown: str | None,
    label: str | None,
    effective_from: date | None,
    clear_effective_from: bool,
) -> DocumentVersion:
    """Sửa bản nháp (nội dung, nhãn, ngày hiệu lực dự kiến). Khóa lạc quan theo `updated_at`."""
    version = await _require_version(session, document_id, version_id)
    if version.status != VersionStatus.DRAFT:
        raise PortalError(409, "VERSION_NOT_EDITABLE", "portal.version_not_editable")
    if version.updated_at != expected_updated_at:
        raise PortalError(409, "VERSION_CONFLICT", "portal.version_conflict")

    changed: list[str] = []
    if markdown is not None and markdown != version.markdown:
        version.markdown = _check_markdown(markdown)
        version.content_checksum = checksum_of(markdown)
        version.source = VersionSource.EDITED.value
        # Đo lại cấu trúc nhưng KHÔNG tự thăng tiêu đề: HR đã sửa tay, không áp lại thứ họ vừa bỏ.
        _, structure = analyze_structure(markdown, infer=False)
        version.quality_report = {**version.quality_report, "structure": structure.as_dict()}
        changed.append("markdown")
    if label is not None and label != version.version_label:
        new_label = _clean_label(label)
        if await _label_taken(session, document_id, new_label, except_id=version.id):
            raise PortalError(409, "VERSION_LABEL_EXISTS", "portal.version_label_exists")
        version.version_label = new_label
        changed.append("label")
    if clear_effective_from and version.effective_from is not None:
        version.effective_from = None
        changed.append("effective_from")
    elif effective_from is not None and effective_from != version.effective_from:
        version.effective_from = effective_from
        changed.append("effective_from")

    if changed:
        version.updated_by = actor.id
        session.add(_audit(actor, "UPDATE_DRAFT", version, changed=changed))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise PortalError(409, "VERSION_LABEL_EXISTS", "portal.version_label_exists") from exc
    await session.refresh(version)
    return version


async def delete_draft(session: AsyncSession, *, document_id: int, version_id: int, actor: User) -> None:
    version = await _require_version(session, document_id, version_id)
    if version.status != VersionStatus.DRAFT or version.activated_at is not None:
        raise PortalError(409, "VERSION_NOT_DELETABLE", "portal.version_not_deletable")
    session.add(_audit(actor, "DELETE_DRAFT", version))
    await session.delete(version)
    await session.commit()


async def activate_version(
    session: AsyncSession,
    *,
    document_id: int,
    version_id: int,
    actor: User,
    effective_from: date | None,
    today: date,
) -> Job:
    """Xếp job kích hoạt (cắt chunk, embedding, đóng bản cũ, bật bản này). Trả job để giao diện hỏi tiến độ."""
    document = await _require_document(session, document_id)
    if document.status != DocumentStatus.ACTIVE:
        raise PortalError(409, "DOCUMENT_ARCHIVED", "portal.document_archived")
    version = await _require_version(session, document_id, version_id)
    if version.status not in ACTIVATABLE_STATUSES:
        raise PortalError(409, "VERSION_NOT_ACTIVATABLE", "portal.version_not_activatable")
    state = display_state(version.status, version.effective_from, version.effective_to, today)
    if state == "CURRENT":
        raise PortalError(409, "VERSION_ALREADY_CURRENT", "portal.version_already_current")
    if version.status == VersionStatus.DRAFT:
        _check_markdown(version.markdown)

    start = effective_from or version.effective_from or today
    if version.status != VersionStatus.DRAFT and start < today:
        # Đặt lại bản cũ làm bản áp dụng: hiệu lực mới bắt đầu từ hôm nay (lịch sử "ai áp dụng khi nào" ở nhật ký).
        start = today
    previous_status = version.status
    # Đặt PROCESSING ngay để nháp không bị sửa trong lúc job chạy; job hỏng thì trả về `previous_status`.
    version.status = VersionStatus.PROCESSING.value
    version.failure_reason = None
    version.updated_by = actor.id
    try:
        job = await enqueue_job(
            session,
            kind=JobKind.ACTIVATE_VERSION.value,
            payload={
                "version_id": version.id,
                "effective_from": start.isoformat(),
                "previous_status": previous_status,
                "actor_id": actor.id,
            },
            idempotency_key=f"activate:{version.id}",
            created_by=actor.id,
            document_version_id=version.id,
        )
    except Exception:
        await session.rollback()
        raise
    return job


async def _task_counts(session: AsyncSession, document_id: int) -> dict[int, int]:
    rows = await session.execute(
        select(TaskSourceMapping.document_version_id, func.count(func.distinct(TaskSourceMapping.task_template_id)))
        .where(TaskSourceMapping.document_id == document_id)
        .group_by(TaskSourceMapping.document_version_id)
    )
    return {version_id: count for version_id, count in rows.all()}


async def _section_counts(session: AsyncSession, version_ids: list[int]) -> dict[int, int]:
    if not version_ids:
        return {}
    rows = await session.execute(
        select(DocumentSection.version_id, func.count())
        .where(DocumentSection.version_id.in_(version_ids))
        .group_by(DocumentSection.version_id)
    )
    return {version_id: count for version_id, count in rows.all()}


def _item(version: DocumentVersion, uploader: str | None, sections: int, tasks: int, today: date) -> VersionItem:
    structure = version.quality_report.get("structure") or {}
    ai = version.quality_report.get("ai_split")
    return VersionItem(
        id=version.id,
        version_label=version.version_label,
        revision_no=version.revision_no,
        state=display_state(version.status, version.effective_from, version.effective_to, today),
        status=version.status,
        effective_from=version.effective_from,
        effective_to=version.effective_to,
        source=version.source,
        parent_version_id=version.parent_version_id,
        original_filename=version.original_filename,
        uploaded_by_name=uploader,
        created_at=version.created_at,
        updated_at=version.updated_at,
        activated_at=version.activated_at,
        failure_reason=version.failure_reason,
        section_count=sections,
        task_count=tasks,
        structure_quality=structure.get("quality"),
        structure_warnings=tuple(structure.get("warnings", ())),
        ai_split=("APPLIED" if ai and ai.get("applied") else "SKIPPED") if ai else None,
    )


async def list_versions(session: AsyncSession, *, document_id: int, today: date) -> list[VersionItem]:
    await _require_document(session, document_id)
    rows = (
        await session.execute(
            select(DocumentVersion, User.display_name)
            .outerjoin(User, User.id == DocumentVersion.uploaded_by)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.revision_no.desc())
        )
    ).all()
    sections = await _section_counts(session, [version.id for version, _ in rows])
    tasks = await _task_counts(session, document_id)
    return [
        _item(version, name, sections.get(version.id, 0), tasks.get(version.id, 0), today) for version, name in rows
    ]


async def get_version_detail(session: AsyncSession, *, document_id: int, version_id: int, today: date) -> VersionDetail:
    document = await _require_document(session, document_id)
    version = await _require_version(session, document_id, version_id)
    uploader = await session.scalar(select(User.display_name).where(User.id == version.uploaded_by))
    sections = await _section_counts(session, [version.id])
    tasks = await _task_counts(session, document_id)
    return VersionDetail(
        item=_item(version, uploader, sections.get(version.id, 0), tasks.get(version.id, 0), today),
        document_id=document.id,
        document_title=document.title,
        markdown=version.markdown,
        can_edit=version.status == VersionStatus.DRAFT,
    )
