"""Đánh giá 👍/👎 của nhân viên cho từng câu trả lời Viga, và danh sách "chưa hài lòng" ẩn danh cho HR.

- Mỗi câu trả lời một đánh giá (`message_id` duy nhất): bấm lại thì đổi, gỡ thì xóa. Chỉ chủ hội thoại đánh giá được.
- 👎 có lý do chọn nhanh (không bắt buộc) và ghi chú tùy chọn.
- HR chỉ thấy đánh giá của **phòng ban mình** và **ẩn danh**: câu hỏi, phần Viga đã trả lời, lý do, số lần; không thấy tên người
  đánh giá hay cả hội thoại (quyết định 8, mục 0.1). Câu hỏi giống nhau (so khớp không dấu) được gom lại.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import ScalarSelect, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.chat_conversation import ChatConversation
from src.model.chat_message import ChatMessage
from src.model.enums import ChatRole, FeedbackRating, FeedbackReason
from src.model.user import User
from src.model.viga_feedback import VigaFeedback
from src.services.portal.errors import PortalError
from src.services.viga.gaps import team_of
from src.services.viga.guard import normalize_question

COMMENT_MAX_CHARS = 500
EXCERPT_MAX_CHARS = 400
SUMMARY_DAYS = 7


async def set_feedback(
    session: AsyncSession,
    user: User,
    message_id: int,
    *,
    rating: FeedbackRating,
    reason: FeedbackReason | None = None,
    comment: str | None = None,
) -> VigaFeedback:
    row = (
        await session.execute(
            select(ChatMessage, ChatConversation.user_id)
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(ChatMessage.id == message_id)
        )
    ).one_or_none()
    # Người khác hoặc không có thì cùng trả 404 (không lộ sự tồn tại); chỉ câu trả lời của Viga mới đánh giá được.
    if row is None or row[1] != user.id or row[0].role != ChatRole.ASSISTANT.value:
        raise PortalError(404, "MESSAGE_NOT_FOUND", "viga.message_not_found")

    clean_comment = " ".join((comment or "").split())[:COMMENT_MAX_CHARS] or None
    is_down = rating == FeedbackRating.DOWN
    existing = await session.scalar(select(VigaFeedback).where(VigaFeedback.message_id == message_id))
    if existing is None:
        existing = VigaFeedback(message_id=message_id, user_id=user.id, rating=rating.value)
        session.add(existing)
    existing.team_id = await team_of(session, user.id)
    existing.rating = rating.value
    existing.reason = reason.value if is_down and reason else None
    existing.comment = clean_comment if is_down else None
    existing.resolved_at = None  # đổi ý hoặc bổ sung lý do thì mở lại cho HR xem
    await session.commit()
    await session.refresh(existing)
    return existing


async def clear_feedback(session: AsyncSession, user: User, message_id: int) -> None:
    feedback = await session.scalar(
        select(VigaFeedback).where(VigaFeedback.message_id == message_id, VigaFeedback.user_id == user.id)
    )
    if feedback is not None:
        await session.delete(feedback)
        await session.commit()


async def feedback_by_message(session: AsyncSession, message_ids: list[int]) -> dict[int, VigaFeedback]:
    if not message_ids:
        return {}
    rows = await session.scalars(select(VigaFeedback).where(VigaFeedback.message_id.in_(message_ids)))
    return {row.message_id: row for row in rows.all()}


def _asked_question() -> ScalarSelect[str]:
    """Câu hỏi của nhân viên ngay trước câu trả lời được đánh giá (cùng hội thoại)."""
    return (
        select(ChatMessage.content)
        .where(
            ChatMessage.conversation_id == ChatConversation.id,
            ChatMessage.role == ChatRole.USER.value,
            ChatMessage.id < VigaFeedback.message_id,
        )
        .order_by(ChatMessage.id.desc())
        .limit(1)
        .correlate(ChatConversation, VigaFeedback)
        .scalar_subquery()
    )


@dataclass(frozen=True)
class DissatisfiedGroup:
    id: int  # mã một đánh giá đại diện của nhóm (dùng để đánh dấu đã xử lý cả nhóm)
    question_text: str
    answer_excerpt: str
    occurrences: int
    reasons: list[str]
    comments: list[str]
    first_at: datetime
    last_at: datetime
    resolved: bool


async def list_dissatisfied(
    session: AsyncSession, *, team_id: int | None, include_resolved: bool
) -> list[DissatisfiedGroup]:
    """Các nhóm câu hỏi bị 👎 trong phạm vi `team_id` (None = mọi phòng ban, dành cho ADMIN), ẩn danh."""
    question = _asked_question()
    query = (
        select(VigaFeedback, ChatMessage.content, question)
        .join(ChatMessage, ChatMessage.id == VigaFeedback.message_id)
        .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
        .where(VigaFeedback.rating == FeedbackRating.DOWN.value)
        .order_by(VigaFeedback.updated_at.desc())
    )
    if team_id is not None:
        query = query.where(VigaFeedback.team_id == team_id)
    groups: dict[str, list[tuple[VigaFeedback, str, str]]] = {}
    for feedback, answer, asked in (await session.execute(query)).all():
        text = " ".join((asked or "").split())
        if text:
            groups.setdefault(normalize_question(text), []).append((feedback, answer, text))

    result: list[DissatisfiedGroup] = []
    for items in groups.values():
        unresolved = [item for item in items if item[0].resolved_at is None]
        resolved = not unresolved
        if resolved and not include_resolved:
            continue
        latest = items[0]
        reasons = list(dict.fromkeys(item[0].reason for item in items if item[0].reason))
        comments = [item[0].comment for item in items if item[0].comment][:3]
        result.append(
            DissatisfiedGroup(
                id=(unresolved or items)[0][0].id,
                question_text=latest[2],
                answer_excerpt=" ".join(latest[1].split())[:EXCERPT_MAX_CHARS],
                occurrences=len(items),
                reasons=reasons,
                comments=[c for c in comments if c],
                first_at=min(item[0].created_at for item in items),
                last_at=max(item[0].updated_at for item in items),
                resolved=resolved,
            )
        )
    return sorted(result, key=lambda g: (g.resolved, -g.occurrences, -g.last_at.timestamp()))


async def resolve_dissatisfied(session: AsyncSession, *, feedback_id: int, team_id: int | None) -> int:
    """Đánh dấu đã xử lý cả nhóm câu hỏi giống `feedback_id` (cùng phòng ban). Trả số đánh giá đã đóng."""
    feedback = await session.get(VigaFeedback, feedback_id)
    if (
        feedback is None
        or feedback.rating != FeedbackRating.DOWN.value
        or (team_id is not None and feedback.team_id != team_id)
    ):
        raise PortalError(404, "FEEDBACK_NOT_FOUND", "portal.feedback_not_found")
    open_ids = (
        await session.scalars(
            select(VigaFeedback.id).where(
                VigaFeedback.team_id == feedback.team_id
                if feedback.team_id is not None
                else VigaFeedback.team_id.is_(None),
                VigaFeedback.rating == FeedbackRating.DOWN.value,
                VigaFeedback.resolved_at.is_(None),
            )
        )
    ).all()
    asked = await _questions_of(session, [*open_ids, feedback_id])
    wanted = normalize_question(asked.get(feedback_id, ""))
    ids = [fid for fid in open_ids if wanted and normalize_question(asked.get(fid, "")) == wanted]
    if ids:
        await session.execute(update(VigaFeedback).where(VigaFeedback.id.in_(ids)).values(resolved_at=func.now()))
    await session.commit()
    return len(ids)


async def scoped_dissatisfied(
    session: AsyncSession, *, feedback_id: int, team_id: int | None
) -> tuple[VigaFeedback, str]:
    """Một đánh giá 👎 trong phạm vi `team_id` (None = ADMIN) và câu hỏi gốc của nó; không có hoặc ngoài phạm vi thì 404."""
    feedback = await session.get(VigaFeedback, feedback_id)
    if (
        feedback is None
        or feedback.rating != FeedbackRating.DOWN.value
        or (team_id is not None and feedback.team_id != team_id)
    ):
        raise PortalError(404, "FEEDBACK_NOT_FOUND", "portal.feedback_not_found")
    question = (await _questions_of(session, [feedback_id])).get(feedback_id, "")
    if not question:
        raise PortalError(404, "FEEDBACK_NOT_FOUND", "portal.feedback_not_found")
    return feedback, question


async def _questions_of(session: AsyncSession, feedback_ids: list[int]) -> dict[int, str]:
    if not feedback_ids:
        return {}
    rows = (
        await session.execute(
            select(VigaFeedback.id, _asked_question())
            .join(ChatMessage, ChatMessage.id == VigaFeedback.message_id)
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(VigaFeedback.id.in_(feedback_ids))
        )
    ).all()
    return {fid: " ".join((text or "").split()) for fid, text in rows}


@dataclass(frozen=True)
class SatisfactionSummary:
    up: int
    down: int
    open_down: int  # 👎 chưa xử lý

    @property
    def satisfaction_percent(self) -> int | None:
        total = self.up + self.down
        return round(100 * self.up / total) if total else None


async def satisfaction_summary(
    session: AsyncSession, *, team_id: int | None, now: datetime | None = None
) -> SatisfactionSummary:
    """Số 👍/👎 trong 7 ngày gần nhất (phạm vi `team_id`; None = mọi phòng ban) và số 👎 chưa xử lý."""
    since = (now or datetime.now(UTC)) - timedelta(days=SUMMARY_DAYS)
    base = select(VigaFeedback.rating, func.count(), VigaFeedback.resolved_at.is_(None)).group_by(
        VigaFeedback.rating, VigaFeedback.resolved_at.is_(None)
    )
    base = base.where(VigaFeedback.updated_at >= since)
    if team_id is not None:
        base = base.where(VigaFeedback.team_id == team_id)
    up = down = open_down = 0
    for rating, count, is_open in (await session.execute(base)).all():
        if rating == FeedbackRating.UP.value:
            up += int(count)
        else:
            down += int(count)
            if is_open:
                open_down += int(count)
    return SatisfactionSummary(up=up, down=down, open_down=open_down)
