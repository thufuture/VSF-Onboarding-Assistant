"""Wrapper mỏng gọi `ingest_document()` có sẵn cho HR upload qua web (plan-portal/P4B/P4B.md mục 8.3).

Không viết lại logic parse/chunk/embed — chỉ lo phần HTTP-specific: ghi `UploadFile` ra file tạm
(`ingest_document` cần `Path`, không nhận bytes trực tiếp) và dọn file tạm kể cả khi lỗi.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.model.document_version import DocumentVersion
from src.model.enums import Confidentiality, ContentKind
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.ingest_service import IngestResult, ingest_document
from src.services.ingest.storage import StoragePort
from src.services.portal.errors import PortalError


async def ingest_uploaded_document(
    session: AsyncSession,
    *,
    file: UploadFile,
    category_slug: str,
    owner_email: str,
    title: str,
    source_key: str,
    version_label: str,
    effective_from: date,
    embedding: EmbeddingPort,
    storage: StoragePort,
) -> IngestResult:
    suffix = Path(file.filename or "").suffix
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        return await ingest_document(
            session,
            file_path=tmp_path,
            category_slug=category_slug,
            owner_email=owner_email,
            title=title,
            source_key=source_key,
            version_label=version_label,
            effective_from=effective_from,
            content_kind=ContentKind.GENERAL.value,
            confidentiality=Confidentiality.INTERNAL.value,
            embedding=embedding,
            storage=storage,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class OriginalDocumentLocation:
    """Nơi lấy lại file gốc để tải xuống — KHÔNG nhảy tới đúng đoạn trong file gốc (xem docstring
    `DocumentContentResponseDTO` bên chat: chỉ có bản Markdown mới cuộn được tới đúng section)."""

    kind: Literal["url", "local_file"]
    value: str  # "url": secure_url Cloudinary; "local_file": đường dẫn tuyệt đối trên đĩa
    filename: str
    mime_type: str


async def resolve_original_document(
    session: AsyncSession, *, document_version_id: int, settings: Settings
) -> OriginalDocumentLocation:
    version = await session.get(DocumentVersion, document_version_id)
    if version is None:
        raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
    if settings.storage_provider == "cloudinary":
        return OriginalDocumentLocation(
            kind="url", value=version.storage_key, filename=version.original_filename, mime_type=version.mime_type
        )
    path = Path(settings.storage_path) / version.storage_key
    return OriginalDocumentLocation(
        kind="local_file", value=str(path), filename=version.original_filename, mime_type=version.mime_type
    )
