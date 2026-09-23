"""Điều phối 2-B: parse -> section/chunk -> tách từ -> embedding -> lưu file -> ghi DB (một transaction).

Kế hoạch: docs/chatbot-vsf/plan/phase-2/2-b-nap-tai-lieu-ke-hoach-chi-tiet.md, mục 2 (kiến trúc) và
mục 11 (xử lý ngoại lệ: 0 chunk, lỗi embedding, idempotent theo content_checksum, transaction/rollback).
"""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import VersionStatus
from src.model.user import User
from src.services.ingest.chunker import ChunkDraft, SectionDraft, split_into_chunks, split_into_sections
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.lexical import to_lexical_text
from src.services.ingest.parser import ParseError, parse_document
from src.services.ingest.storage import StoragePort


class IngestError(Exception):
    """Nạp tài liệu thất bại — không có gì được ghi vào DB (transaction chưa mở hoặc đã rollback)."""


@dataclass(frozen=True)
class IngestResult:
    document_id: int
    version_id: int
    section_count: int
    chunk_count: int
    created: bool  # False: đã có sẵn (cùng content_checksum), không nạp lại (idempotent, INV5)


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
            section_count, chunk_count = await _count_children(session, existing_version.id)
            return IngestResult(document.id, existing_version.id, section_count, chunk_count, created=False)
        raise IngestError(
            f"phiên bản '{version_label}' của tài liệu '{title}' đã tồn tại với nội dung khác (INV5) — "
            "dùng nhãn phiên bản mới nếu nội dung thật sự đã đổi"
        )

    sections_draft = split_into_sections(parsed.markdown)
    chunks_by_section: list[tuple[SectionDraft, list[ChunkDraft]]] = [
        (section, split_into_chunks(section)) for section in sections_draft
    ]
    all_chunks: list[ChunkDraft] = [chunk for _, chunks in chunks_by_section for chunk in chunks]
    if not all_chunks:
        # Cổng cứng (mục 11.3): 0 chunk thì không được ghi gì, không có version FAILED lưu lại ở 2-B
        # (CLI đồng bộ, không có bảng job theo dõi FAILED — đủ dùng ở đây là báo lỗi rõ ràng và dừng).
        raise IngestError("không tách được đoạn nào từ tài liệu (0 chunk) — không cho phép nạp (mục 11.3)")

    embedding_texts = [_embedding_text(chunk) for chunk in all_chunks]
    try:
        vectors = await embedding.embed(embedding_texts)
    except Exception as exc:
        raise IngestError(f"embedding thất bại, không ghi dữ liệu nửa vời (mục 11.4/11.5): {exc}") from exc
    if len(vectors) != len(all_chunks) or any(len(vector) != embedding.dimension for vector in vectors):
        raise IngestError("số vector trả về không khớp số chunk hoặc sai số chiều — dừng, không ghi DB")

    try:
        storage_key = await storage.store(
            file_path.read_bytes(), content_checksum=parsed.content_checksum, filename=file_path.name
        )
    except Exception as exc:
        raise IngestError(f"lưu file gốc thất bại: {exc}") from exc

    version = DocumentVersion(
        document_id=document.id,
        version_label=version_label,
        revision_no=await _next_revision_no(session, document.id),
        status=VersionStatus.ACTIVE.value,
        original_filename=file_path.name,
        mime_type=mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
        size_bytes=parsed.size_bytes,
        storage_key=storage_key,
        file_checksum=parsed.file_checksum,
        content_checksum=parsed.content_checksum,
        parser="markitdown",
        markdown=parsed.markdown,
        quality_report={"has_embedded_images": parsed.has_embedded_images},
        effective_from=effective_from,
        embedding_model_version=embedding.model_version,
        uploaded_by=owner.id,
        activated_at=datetime.now(UTC),
    )
    session.add(version)
    await session.flush()  # cần version.id trước khi ghi section/chunk

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

    for global_index, (chunk, vector) in enumerate(zip(all_chunks, vectors, strict=True)):
        session.add(
            DocumentChunk(
                section_id=section_id_by_index[chunk.section_index],
                version_id=version.id,
                chunk_index=global_index,
                heading=chunk.heading,
                content=chunk.content,
                embedding_text=_embedding_text(chunk),
                lexical_text=to_lexical_text(chunk.content),
                content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                token_count=chunk.token_count,
                embedding_model_version=embedding.model_version,
                embedding=vector,
            )
        )

    session.add(
        AuditLog(
            actor_id=owner.id,
            action="INGEST_DOCUMENT",
            entity_type="document_version",
            entity_id=str(version.id),  # version.id đã có từ flush ở trên
            after={
                "document_id": document.id,
                "version_label": version_label,
                "section_count": len(sections_draft),
                "chunk_count": len(all_chunks),
            },
        )
    )

    await session.commit()
    return IngestResult(document.id, version.id, len(sections_draft), len(all_chunks), created=True)


def _embedding_text(chunk: ChunkDraft) -> str:
    return f"{chunk.heading}\n{chunk.content}" if chunk.heading else chunk.content


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


async def _count_children(session: AsyncSession, version_id: int) -> tuple[int, int]:
    section_count = await session.scalar(
        select(func.count()).select_from(DocumentSection).where(DocumentSection.version_id == version_id)
    )
    chunk_count = await session.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.version_id == version_id)
    )
    return int(section_count or 0), int(chunk_count or 0)
