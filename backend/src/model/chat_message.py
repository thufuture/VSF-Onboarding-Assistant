from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column
from src.model.enums import ChatRole, check_in


class ChatMessage(Base):
    """Một lượt trong cuộc trò chuyện. Câu trả lời của Viga lưu thêm `response_type` và `payload` (nguồn trích,
    việc chặn, hành động gợi ý) để mở lại cuộc trò chuyện hiện đúng như lúc đã hỏi."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        check_in("role", ChatRole),
        Index("ix_chat_messages_conversation_id_id", "conversation_id", "id"),
    )

    id: Mapped[int] = id_column()
    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    response_type: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_column()
