"""Vòng đời phiên bản tài liệu dùng chung cho CLI nạp, trang Tài liệu (nháp, kích hoạt) và job nền.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 16.3 và 16.5.

Quy tắc cốt lõi: một tài liệu có đúng **một bản đang áp dụng tại một ngày**. Kích hoạt một phiên bản làm trong
**cùng transaction với việc ghi section/chunk**: đóng các bản ACTIVE khác rồi bật bản này. Lỗi giữa chừng thì
không đổi gì, bản cũ vẫn chạy (đây chính là cách sửa lỗi 1 ở mục 10.2).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.audit_log import AuditLog
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import VersionStatus
from src.services.ingest.chunker import ChunkDraft, SectionDraft
from src.services.ingest.lexical import to_lexical_text

DisplayState = Literal["DRAFT", "PROCESSING", "SCHEDULED", "CURRENT", "SUPERSEDED", "FAILED"]


def display_state(status: str, effective_from: date | None, effective_to: date | None, today: date) -> DisplayState:
    """Trạng thái hiển thị (mục 16.3). `ACTIVE` đã hết hạn do bản mới có hiệu lực từ ngày sau thì coi là đã thay thế."""
    if status == VersionStatus.DRAFT or status == VersionStatus.PENDING_REVIEW:
        return "DRAFT"
    if status == VersionStatus.PROCESSING:
        return "PROCESSING"
    if status == VersionStatus.FAILED:
        return "FAILED"
    if status == VersionStatus.ARCHIVED:
        return "SUPERSEDED"
    if effective_from is not None and effective_from > today:
        return "SCHEDULED"
    if effective_to is not None and effective_to < today:
        return "SUPERSEDED"
    return "CURRENT"


async def get_current_version(session: AsyncSession, document_id: int, today: date) -> DocumentVersion | None:
    """Bản đang áp dụng của tài liệu tại `today` (trạng thái ACTIVE và `today` nằm trong khoảng hiệu lực)."""
    version: DocumentVersion | None = await session.scalar(
        select(DocumentVersion)
        .where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.status == VersionStatus.ACTIVE,
            (DocumentVersion.effective_from.is_(None)) | (DocumentVersion.effective_from <= today),
            (DocumentVersion.effective_to.is_(None)) | (DocumentVersion.effective_to >= today),
        )
        .order_by(DocumentVersion.revision_no.desc())
        .limit(1)
    )
    return version


def embedding_text_of(chunk: ChunkDraft) -> str:
    return f"{chunk.heading}\n{chunk.content}" if chunk.heading else chunk.content


def checksum_of(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


async def write_sections_and_chunks(
    session: AsyncSession,
    *,
    version: DocumentVersion,
    chunks_by_section: Sequence[tuple[SectionDraft, Sequence[ChunkDraft]]],
    vectors: Sequence[Sequence[float]],
    embedding_model_version: str,
) -> None:
    """Ghi section rồi chunk của `version` (đã `flush` để có `version.id`). Vector xếp theo thứ tự chunk phẳng."""
    section_id_by_index: dict[int, int] = {}
    for section, _chunks in chunks_by_section:
        row = DocumentSection(
            version_id=version.id,
            section_index=section.section_index,
            heading=section.heading,
            content=section.content,
            token_count=section.token_count,
        )
        session.add(row)
        await session.flush()  # cần row.id để chunk trỏ đúng section_id
        section_id_by_index[section.section_index] = row.id

    all_chunks = [chunk for _, chunks in chunks_by_section for chunk in chunks]
    for global_index, (chunk, vector) in enumerate(zip(all_chunks, vectors, strict=True)):
        session.add(
            DocumentChunk(
                section_id=section_id_by_index[chunk.section_index],
                version_id=version.id,
                chunk_index=global_index,
                heading=chunk.heading,
                content=chunk.content,
                embedding_text=embedding_text_of(chunk),
                lexical_text=to_lexical_text(chunk.content),
                content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                token_count=chunk.token_count,
                embedding_model_version=embedding_model_version,
                embedding=list(vector),
            )
        )


async def delete_sections_and_chunks(session: AsyncSession, version_id: int) -> None:
    await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id == version_id))
    await session.execute(delete(DocumentSection).where(DocumentSection.version_id == version_id))


async def count_children(session: AsyncSession, version_id: int) -> tuple[int, int]:
    sections = await session.scalar(
        select(func.count()).select_from(DocumentSection).where(DocumentSection.version_id == version_id)
    )
    chunks = await session.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.version_id == version_id)
    )
    return int(sections or 0), int(chunks or 0)


async def activate_version_row(
    session: AsyncSession,
    *,
    version: DocumentVersion,
    effective_from: date,
    actor_id: int,
    today: date,
) -> list[int]:
    """Bật `version` thành ACTIVE từ `effective_from` và đóng các bản ACTIVE khác của cùng tài liệu.

    Trả về mã các bản bị đóng/rút ngắn. Gọi **bên trong transaction** đang ghi section/chunk; không `commit` ở đây.

    - Bản khác đang/đã có hiệu lực trước ngày mới: `effective_to = effective_from - 1 ngày`. Nếu hiệu lực đó đã
      qua (hoặc hiệu lực mới bắt đầu từ hôm nay trở về trước) thì chuyển `ARCHIVED` luôn (hiển thị "Đã thay thế").
    - Bản khác hẹn hiệu lực từ ngày mới trở đi (sẽ chồng ngày): chuyển `ARCHIVED`.
    - Ngày mới ở tương lai: bản đang áp dụng **vẫn ACTIVE** tới hết ngày trước đó (Viga tiếp tục dùng bản cũ).
    """
    others = (
        await session.scalars(
            select(DocumentVersion)
            .where(
                DocumentVersion.document_id == version.document_id,
                DocumentVersion.id != version.id,
                DocumentVersion.status == VersionStatus.ACTIVE,
            )
            .with_for_update()
        )
    ).all()
    closed: list[int] = []
    day_before = effective_from - timedelta(days=1)
    for other in others:
        starts = other.effective_from
        if starts is not None and starts >= effective_from:
            # Chồng ngày với bản mới: bản này không còn chỗ, đóng hẳn.
            other.status = VersionStatus.ARCHIVED.value
            other.effective_to = starts
        else:
            other.effective_to = day_before
            if effective_from <= today:
                other.status = VersionStatus.ARCHIVED.value
        closed.append(other.id)

    # Đóng các bản khác TRƯỚC khi bật bản này: ràng buộc chống chồng ngày kiểm ngay từng câu UPDATE, không đợi hết
    # transaction, nên thứ tự ghi quan trọng.
    await session.flush()

    version.status = VersionStatus.ACTIVE.value
    version.effective_from = effective_from
    version.effective_to = None
    version.activated_at = datetime.now(UTC)
    version.failure_reason = None
    version.updated_by = actor_id
    await session.flush()  # để ràng buộc không chồng ngày được kiểm ngay trong transaction này

    session.add(
        AuditLog(
            actor_id=actor_id,
            action="ACTIVATE_VERSION",
            entity_type="document_version",
            entity_id=str(version.id),
            after={
                "document_id": version.document_id,
                "version_label": version.version_label,
                "effective_from": effective_from.isoformat(),
                "closed_version_ids": closed,
            },
        )
    )
    return closed
