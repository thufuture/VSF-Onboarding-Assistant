"""Ảnh và video đính kèm ticket: kiểm tra loại và dung lượng, đẩy lên Cloudinary, giữ URL, gắn vào tin nhắn khi gửi.

Giới hạn: ảnh JPG/PNG/WebP/GIF tối đa 10 MB, video MP4/WebM/MOV tối đa 50 MB, tối đa 5 tệp mỗi tin nhắn.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.ticket_attachment import TicketAttachment
from src.model.user import User
from src.services.ingest.storage import MediaNotSupportedError, StoragePort
from src.services.portal.errors import PortalError

MAX_PER_MESSAGE = 5
IMAGE_TYPES = {"image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"}, "image/gif": {".gif"}}
VIDEO_TYPES = {"video/mp4": {".mp4"}, "video/webm": {".webm"}, "video/quicktime": {".mov"}}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class AttachmentKind:
    kind: str
    limit: int


def classify(content_type: str, filename: str) -> AttachmentKind:
    """Loại tệp theo `content_type` và đuôi file (phải khớp nhau); sai thì báo lỗi rõ ràng."""
    suffix = Path(filename).suffix.lower()
    if content_type in IMAGE_TYPES and suffix in IMAGE_TYPES[content_type]:
        return AttachmentKind("IMAGE", MAX_IMAGE_BYTES)
    if content_type in VIDEO_TYPES and suffix in VIDEO_TYPES[content_type]:
        return AttachmentKind("VIDEO", MAX_VIDEO_BYTES)
    raise PortalError(415, "ATTACHMENT_TYPE_NOT_ALLOWED", "portal.attachment_type_not_allowed")


async def upload(
    session: AsyncSession, user: User, storage: StoragePort, *, filename: str, content_type: str, content: bytes
) -> TicketAttachment:
    info = classify(content_type, filename)
    if not content:
        raise PortalError(422, "ATTACHMENT_EMPTY", "portal.attachment_empty")
    if len(content) > info.limit:
        raise PortalError(413, "ATTACHMENT_TOO_LARGE", "portal.attachment_too_large")
    try:
        url = await storage.store_media(content, filename=filename, kind=info.kind)
    except MediaNotSupportedError as exc:
        raise PortalError(503, "ATTACHMENTS_UNAVAILABLE", "portal.attachments_unavailable") from exc
    except Exception as exc:  # mạng/khóa Cloudinary lỗi: không để thành 500 khó hiểu
        raise PortalError(502, "ATTACHMENT_UPLOAD_FAILED", "portal.attachment_upload_failed") from exc
    row = TicketAttachment(
        uploaded_by_user_id=user.id,
        kind=info.kind,
        url=url,
        filename=Path(filename).name[:255],
        content_type=content_type,
        size_bytes=len(content),
    )
    session.add(row)
    await session.commit()
    return row


async def discard(session: AsyncSession, user: User, attachment_id: int) -> None:
    """Bỏ một tệp đang chờ (chưa gắn vào tin nhắn nào) của chính người tải."""
    row = await session.get(TicketAttachment, attachment_id)
    if row is None or row.uploaded_by_user_id != user.id or row.ticket_message_id is not None:
        raise PortalError(404, "ATTACHMENT_NOT_FOUND", "portal.attachment_not_found")
    await session.delete(row)
    await session.commit()


async def link(session: AsyncSession, user: User, attachment_ids: Sequence[int], message_id: int) -> None:
    """Gắn các tệp đang chờ của `user` vào tin nhắn. Mã lạ hoặc tệp đã gắn bị bỏ qua (không lộ tệp của người khác)."""
    ids = list(dict.fromkeys(attachment_ids))
    if len(ids) > MAX_PER_MESSAGE:
        raise PortalError(422, "ATTACHMENT_TOO_MANY", "portal.attachment_too_many")
    if not ids:
        return
    rows = (
        await session.scalars(
            select(TicketAttachment).where(
                TicketAttachment.id.in_(ids),
                TicketAttachment.uploaded_by_user_id == user.id,
                TicketAttachment.ticket_message_id.is_(None),
            )
        )
    ).all()
    for row in rows:
        row.ticket_message_id = message_id


async def by_message(session: AsyncSession, message_ids: Sequence[int]) -> dict[int, list[dict[str, object]]]:
    if not message_ids:
        return {}
    rows = (
        await session.scalars(
            select(TicketAttachment)
            .where(TicketAttachment.ticket_message_id.in_(list(message_ids)))
            .order_by(TicketAttachment.id)
        )
    ).all()
    result: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        assert row.ticket_message_id is not None
        result.setdefault(row.ticket_message_id, []).append(view(row))
    return result


def view(row: TicketAttachment) -> dict[str, object]:
    return {
        "id": row.id,
        "kind": row.kind,
        "url": row.url,
        "filename": row.filename,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
    }
