from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column


class ContentGap(Base):
    """P0A D9: mỗi lần Viga trả 'chưa có căn cứ' thì ghi lại ở đây, gắn `team_id` của người hỏi (không
    phải của tài liệu — tài liệu dùng chung có thể `team_id = NULL`) để HR chỉ thấy gap của phòng ban mình."""

    __tablename__ = "content_gaps"
    __table_args__ = (Index("ix_content_gaps_team_id", "team_id"),)

    id: Mapped[int] = id_column()
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    asked_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    related_employee_task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employee_tasks.id", ondelete="SET NULL")
    )
    question_text: Mapped[str] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
