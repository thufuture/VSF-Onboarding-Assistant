from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, updated_at_column


class TicketRead(Base):
    """Mỗi người đã xem một ticket tới tin nhắn nào. Ticket "chưa đọc" khi có tin của phía bên kia mới hơn mốc này."""

    __tablename__ = "ticket_reads"

    ticket_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_read_message_id: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = updated_at_column()
