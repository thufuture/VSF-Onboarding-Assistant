from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column


class ChatConversation(Base):
    """Một cuộc trò chuyện của một nhân viên với Viga (kiểu ChatGPT: nhiều cuộc, xem lại, mở cuộc mới, xóa).

    Chỉ chủ sở hữu đọc được (HR không đọc hội thoại cá nhân). Tự xóa sau thời hạn lưu (`chat_retention_days`);
    nội dung KHÔNG gửi sang Langfuse (INV8).
    """

    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("ix_chat_conversations_user_id_updated_at", "user_id", "updated_at"),
        Index("ix_chat_conversations_updated_at", "updated_at"),
    )

    id: Mapped[int] = id_column()
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
