from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column


class EmployeeJourney(Base):
    """Instance snapshot từ 1 version của JourneyTemplate — publish version mới KHÔNG tự đổi journey
    đang chạy (P0A D2); HR chủ động chọn giữ nguyên hoặc migrate cho từng journey (chưa tự động ở MVP)."""

    __tablename__ = "employee_journeys"
    __table_args__ = (
        Index("ix_employee_journeys_user_id", "user_id"),
        Index("ix_employee_journeys_team_id", "team_id"),
    )

    id: Mapped[int] = id_column()
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    journey_template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("journey_templates.id", ondelete="RESTRICT")
    )
    # Scope theo team của CHÍNH nhân viên tại thời điểm bắt đầu journey (không suy ra từ team_members mỗi lần đọc,
    # để lịch sử ổn định nếu sau này nhân viên đổi phòng ban — xem plan-portal/P1/P1.md mục 0).
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    started_at: Mapped[datetime] = mapped_column(TimestampTZ, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(TimestampTZ)  # soft delete — P0A §5 retention
    created_at: Mapped[datetime] = created_at_column()
