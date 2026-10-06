from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column


class EmployeeStage(Base):
    """Một ngày trong lộ trình RIÊNG của nhân viên (bản sao của một StageVersion lúc tạo hoặc lúc cập nhật)."""

    __tablename__ = "employee_stages"
    __table_args__ = (Index("ix_employee_stages_employee_journey_id", "employee_journey_id"),)

    id: Mapped[int] = id_column()
    employee_journey_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employee_journeys.id", ondelete="CASCADE"))
    # Danh tính của "ngày" (ổn định qua các phiên bản); NULL nếu ngày mẫu đã bị xóa.
    journey_stage_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("journey_stages.id", ondelete="SET NULL")
    )
    # Phiên bản đã sao chép; so với bản đang áp dụng để biết "có bản mới".
    source_stage_version_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stage_versions.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
