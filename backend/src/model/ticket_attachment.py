from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column


class TicketAttachment(Base):
    """Ảnh hoặc video đính kèm một tin nhắn của ticket. File nằm trên Cloudinary, DB chỉ giữ URL.

    Tải lên trước (`ticket_message_id` còn NULL = đang chờ), rồi gắn vào tin nhắn khi gửi ticket hoặc trả lời.
    """

    __tablename__ = "ticket_attachments"
    __table_args__ = (
        Index("ix_ticket_attachments_ticket_message_id", "ticket_message_id"),
        Index("ix_ticket_attachments_uploader_pending", "uploaded_by_user_id", "ticket_message_id"),
    )

    id: Mapped[int] = id_column()
    uploaded_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    ticket_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ticket_messages.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(8))  # IMAGE | VIDEO
    url: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at_column()
