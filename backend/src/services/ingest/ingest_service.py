"""Điều phối 2-B (đường CLI, đồng bộ): parse -> section/chunk -> embedding -> lưu file -> ghi DB (một transaction).

Kế hoạch: docs/chatbot-vsf/plan/phase-2/2-b-nap-tai-lieu-ke-hoach-chi-tiet.md, mục 2 (kiến trúc) và
mục 11 (xử lý ngoại lệ: 0 chunk, lỗi embedding, idempotent theo content_checksum, transaction/rollback).

Trang Tài liệu của portal dùng đường khác (bản nháp rồi kích hoạt chạy nền, `document_version_service`), nhưng cả hai
dùng chung `version_lifecycle`: ghi section/chunk và đóng bản cũ **trong cùng transaction** (sửa lỗi 1, mục 10.2).
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.observability.call_metrics import call_context
from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_version import DocumentVersion
from src.model.enums import VersionStatus
from src.model.user import User
from src.services.ingest.chunker import ChunkDraft, SectionDraft, split_into_chunks, split_into_sections
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.parser import ParseError, parse_document
from src.services.ingest.storage import StoragePort
from src.services.ingest.structure import analyze_structure, subdivide_sections
from src.services.ingest.version_lifecycle import (
    activate_version_row,
    count_children,
    embedding_text_of,
    write_sections_and_chunks,
)

DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"


class IngestError(Exception):
    """Nạp tài liệu thất bại — không có gì được ghi vào DB (transaction chưa mở hoặc đã rollback)."""


@dataclass(frozen=True)
class IngestResult:
    document_id: int
    version_id: int
    section_count: int
    chunk_count: int
    created: bool  # False: đã có sẵn (cùng content_checksum), không nạp lại (idempotent, INV5)


def chunk_markdown(markdown: str) -> tuple[list[tuple[SectionDraft, list[ChunkDraft]]], list[ChunkDraft]]:
    """Cắt Markdown thành (section, chunk) và danh sách chunk phẳng theo thứ tự ghi/embedding."""
    sections = subdivide_sections(split_into_sections(markdown))
    chunks_by_section = [(section, split_into_chunks(section)) for section in sections]
    return chunks_by_section, [chunk for _, chunks in chunks_by_section for chunk in chunks]


def today_in(timezone_name: str = DEFAULT_TIMEZONE) -> date:
    from datetime import datetime

    return datetime.now(ZoneInfo(timezone_name)).date()


async def ingest_document(
    session: AsyncSession,
    *,
    file_path: Path,
    category_slug: str,
    owner_email: str,
    title: str,
    source_key: str,
    version_label: str,
    effective_from: date,
    content_kind: str,
    confidentiality: str,
    embedding: EmbeddingPort,
    storage: StoragePort,
) -> IngestResult:
    try:
        parsed = parse_document(file_path)
    except ParseError as exc:
        raise IngestError(str(exc)) from exc

    category = await _require_category(session, category_slug)
    owner = await _require_owner(session, owner_email)
    document = await _get_or_create_document(session, category, owner, source_key, title, content_kind, confidentiality)

    existing_version = await session.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_label == version_label,
        )
    )
    if existing_version is not None:
        if existing_version.content_checksum == parsed.content_checksum:
            section_count, chunk_count = await count_children(session, existing_version.id)
            return IngestResult(document.id, existing_version.id, section_count, chunk_count, created=False)
        raise IngestError(
            f"phiên bản '{version_label}' của tài liệu '{title}' đã tồn tại với nội dung khác (INV5) — "
            "dùng nhãn phiên bản mới nếu nội dung thật sự đã đổi"
        )

    # Thăng tiêu đề giả (nếu file không có heading thật) trước khi cắt; chữ của tài liệu không đổi.
    structured_markdown, structure = analyze_structure(parsed.markdown)
    chunks_by_section, all_chunks = chunk_markdown(structured_markdown)
    if not all_chunks:
        # Cổng cứng (mục 11.3): 0 chunk thì không được ghi gì.
        raise IngestError("không tách được đoạn nào từ tài liệu (0 chunk) — không cho phép nạp (mục 11.3)")

    embedding_texts = [embedding_text_of(chunk) for chunk in all_chunks]
    try:
        with call_context(operation="ingest.embed"):
            vectors = await embedding.embed(embedding_texts)
    except Exception as exc:
        raise IngestError(f"embedding thất bại, không ghi dữ liệu nửa vời (mục 11.4/11.5): {exc}") from exc
    if len(vectors) != len(all_chunks) or any(len(vector) != embedding.dimension for vector in vectors):
        raise IngestError("số vector trả về không khớp số chunk hoặc sai số chiều — dừng, không ghi DB")

    try:
        # Tên file theo checksum của FILE (không phải của Markdown) để hai file khác byte không ghi đè nhau.
        storage_key = await storage.store(
            file_path.read_bytes(), checksum=parsed.file_checksum, filename=file_path.name
        )
    except Exception as exc:
        raise IngestError(f"lưu file gốc thất bại: {exc}") from exc

    version = DocumentVersion(
        document_id=document.id,
        version_label=version_label,
        revision_no=await _next_revision_no(session, document.id),
        status=VersionStatus.PROCESSING.value,
        original_filename=file_path.name,
        mime_type=mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
        size_bytes=parsed.size_bytes,
        storage_key=storage_key,
        file_checksum=parsed.file_checksum,
        content_checksum=parsed.content_checksum,
        parser="markitdown",
        markdown=structured_markdown,
        quality_report={"has_embedded_images": parsed.has_embedded_images, "structure": structure.as_dict()},
        effective_from=effective_from,
        embedding_model_version=embedding.model_version,
        uploaded_by=owner.id,
    )
    session.add(version)
    await session.flush()  # cần version.id trước khi ghi section/chunk

    await write_sections_and_chunks(
        session,
        version=version,
        chunks_by_section=chunks_by_section,
        vectors=vectors,
        embedding_model_version=embedding.model_version,
    )
    # Đóng bản cũ và bật bản này trong cùng transaction (sửa lỗi 1: trước đây bản cũ không bao giờ được đóng).
    await activate_version_row(
        session, version=version, effective_from=effective_from, actor_id=owner.id, today=today_in()
    )

    session.add(
        AuditLog(
            actor_id=owner.id,
            action="INGEST_DOCUMENT",
            entity_type="document_version",
            entity_id=str(version.id),
            after={
                "document_id": document.id,
                "version_label": version_label,
                "section_count": len(chunks_by_section),
                "chunk_count": len(all_chunks),
            },
        )
    )

    await session.commit()
    return IngestResult(document.id, version.id, len(chunks_by_section), len(all_chunks), created=True)


async def _require_category(session: AsyncSession, slug: str) -> DocumentCategory:
    from src.services.ingest.registry_lookup import RegistryLookupError, get_category_by_slug

    try:
        return await get_category_by_slug(session, slug)
    except RegistryLookupError as exc:
        raise IngestError(str(exc)) from exc


async def _require_owner(session: AsyncSession, email: str) -> User:
    from src.services.ingest.registry_lookup import RegistryLookupError, get_user_by_email

    try:
        return await get_user_by_email(session, email)
    except RegistryLookupError as exc:
        raise IngestError(str(exc)) from exc


async def _get_or_create_document(
    session: AsyncSession,
    category: DocumentCategory,
    owner: User,
    source_key: str,
    title: str,
    content_kind: str,
    confidentiality: str,
) -> Document:
    document = await session.scalar(select(Document).where(Document.source_key == source_key))
    if document is not None:
        return document
    document = Document(
        title=title,
        category_id=category.id,
        owner_id=owner.id,
        content_kind=content_kind,
        confidentiality=confidentiality,
        source_key=source_key,
    )
    session.add(document)
    await session.flush()
    return document


async def _next_revision_no(session: AsyncSession, document_id: int) -> int:
    current_max = await session.scalar(
        select(func.max(DocumentVersion.revision_no)).where(DocumentVersion.document_id == document_id)
    )
    return int(current_max or 0) + 1
