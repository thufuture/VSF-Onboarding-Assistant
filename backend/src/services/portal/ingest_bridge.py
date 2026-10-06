"""Tìm lại file gốc của một phiên bản tài liệu để tải xuống (trang Tài liệu của HR).

Tải file lên và tạo bản nháp nằm ở `document_version_service`; kích hoạt chạy nền ở `job_handlers`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.model.document_version import DocumentVersion
from src.services.portal.errors import PortalError


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
