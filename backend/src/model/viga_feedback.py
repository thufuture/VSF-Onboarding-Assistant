from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column, updated_at_column
from src.model.enums import FeedbackRating, check_in


class VigaFeedback(Base):
    """Đánh giá 👍/👎 của nhân viên cho MỘT câu trả lời của Viga (mỗi câu trả lời một đánh giá, bấm lại thì đổi).

    HR chỉ thấy đánh giá theo phòng ban và ẩn danh: `team_id` ghi lúc đánh giá để lọc, không lộ người đánh giá và hội thoại.
    Nội dung câu hỏi/câu trả lời nằm sẵn trong `chat_messages`, bảng này không chép lại.
    """

    __tablename__ = "viga_feedback"
    __table_args__ = (
        check_in("rating", FeedbackRating),
        UniqueConstraint("message_id", name="uq_viga_feedback_message_id"),
        Index("ix_viga_feedback_team_id_rating", "team_id", "rating"),
    )

    id: Mapped[int] = id_column()
    message_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_messages.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="SET NULL"))
    rating: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str | None] = mapped_column(String(24))
    comment: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
