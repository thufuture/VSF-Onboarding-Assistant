from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column, updated_at_column
from src.model.enums import TicketSource, TicketStatus, check_in


class Ticket(Base):
    """P0A D5: vào hàng đợi chung của team; `assigned_hr_id` chỉ set khi 1 HR bấm "Nhận xử lý" (tránh 2 HR
    xử lý trùng). P0A D6: đóng ticket KHÔNG tự đổi trạng thái task liên quan — HR chủ động đổi."""

    __tablename__ = "tickets"
    __table_args__ = (
        check_in("status", TicketStatus),
        check_in("source", TicketSource),
        Index("ix_tickets_created_by_user_id_created_at", "created_by_user_id", "created_at"),
        Index("ix_tickets_team_id", "team_id"),
        Index("ix_tickets_assigned_hr_id", "assigned_hr_id"),
    )

    id: Mapped[int] = id_column()
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    assigned_hr_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    related_employee_task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employee_tasks.id", ondelete="SET NULL")
    )
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), server_default=TicketStatus.OPEN.value)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    # VIGA: nhân viên bấm "Gửi câu hỏi này cho HR" từ một cuộc trò chuyện; MANUAL: tạo tay.
    source: Mapped[str] = mapped_column(String(8), server_default=TicketSource.MANUAL.value)
    conversation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_conversations.id", ondelete="SET NULL")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TimestampTZ)  # soft delete — P0A §5 retention
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
