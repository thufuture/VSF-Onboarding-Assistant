"""Hội thoại kiểu ChatGPT lưu trên máy chủ (mục 6.2): nhiều cuộc, xem lại, mở cuộc mới, đổi tên, xóa.

- Mỗi người **chỉ thấy cuộc của chính mình** (HR không đọc hội thoại cá nhân).
- Giao diện chỉ gửi `conversation_id`; vài lượt gần nhất đọc lại từ DB (một truy vấn có chỉ mục, nhanh hơn nhiều so với một
  lần gọi LLM nên không cần bộ nhớ đệm riêng) và **chỉ** đi vào bước viết lại câu hỏi.
- Giữ `chat_retention_days` ngày rồi tự xóa (quyết định 8, mục 0.1); người dùng xóa được cuộc của mình.
- Nội dung hội thoại không gửi sang Langfuse (INV8).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.chat_conversation import ChatConversation
from src.model.chat_message import ChatMessage
from src.model.enums import ChatRole
from src.model.user import User
from src.services.portal.errors import PortalError

HISTORY_TURNS = 6
TITLE_MAX_CHARS = 60
LIST_LIMIT = 50


def make_title(question: str) -> str:
    """Tiêu đề lấy từ câu hỏi đầu (rẻ, không tốn thêm một lần gọi LLM) — quyết định ở mục 6.2."""
    text = " ".join(question.split())
    return text if len(text) <= TITLE_MAX_CHARS else text[: TITLE_MAX_CHARS - 1].rstrip() + "…"


async def create_conversation(session: AsyncSession, user: User, first_question: str) -> ChatConversation:
    conversation = ChatConversation(user_id=user.id, title=make_title(first_question))
    session.add(conversation)
    await session.flush()
    return conversation


async def get_owned(session: AsyncSession, user: User, conversation_id: int) -> ChatConversation:
    """Cuộc trò chuyện của chính `user`; người khác hoặc không có thì cùng trả 404 (không lộ sự tồn tại)."""
    conversation = await session.get(ChatConversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise PortalError(404, "CONVERSATION_NOT_FOUND", "viga.conversation_not_found")
    return conversation


async def recent_history(
    session: AsyncSession, conversation_id: int, turns: int = HISTORY_TURNS
) -> list[tuple[str, str]]:
    """Các cặp (vai, nội dung) của `turns` lượt gần nhất, cũ trước mới sau."""
    rows = (
        await session.execute(
            select(ChatMessage.role, ChatMessage.content)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id.desc())
            .limit(turns * 2)
        )
    ).all()
    return [(role, content) for role, content in reversed(rows)]


async def append_message(
    session: AsyncSession,
    conversation: ChatConversation,
    *,
    role: ChatRole,
    content: str,
    response_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role=role.value,
        content=content,
        response_type=response_type,
        payload=payload or {},
    )
    session.add(message)
    conversation.updated_at = func.now()
    await session.flush()
    return message


async def list_conversations(session: AsyncSession, user: User, limit: int = LIST_LIMIT) -> list[ChatConversation]:
    rows = await session.scalars(
        select(ChatConversation)
        .where(ChatConversation.user_id == user.id)
        .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
        .limit(limit)
    )
    return list(rows.all())


async def list_messages(session: AsyncSession, conversation: ChatConversation) -> list[ChatMessage]:
    rows = await session.scalars(
        select(ChatMessage).where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.id)
    )
    return list(rows.all())


async def rename(session: AsyncSession, conversation: ChatConversation, title: str) -> ChatConversation:
    clean = make_title(title)
    if not clean:
        raise PortalError(422, "TITLE_REQUIRED", "viga.title_required")
    conversation.title = clean
    await session.commit()
    await session.refresh(conversation)  # `updated_at` do DB cập nhật: nạp lại để đọc được ngoài greenlet
    return conversation


async def delete_conversation(session: AsyncSession, conversation: ChatConversation) -> None:
    await session.delete(conversation)
    await session.commit()


async def purge_expired(session: AsyncSession, retention_days: int, now: datetime | None = None) -> int:
    """Xóa cuộc trò chuyện không hoạt động quá `retention_days` ngày (tin nhắn xóa theo bằng khóa ngoại CASCADE)."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    result = await session.execute(delete(ChatConversation).where(ChatConversation.updated_at < cutoff))
    await session.commit()
    return int(getattr(result, "rowcount", 0) or 0)
