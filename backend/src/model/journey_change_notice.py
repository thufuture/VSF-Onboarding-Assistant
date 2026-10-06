from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column


class JourneyChangeNotice(Base):
    """Thông báo "lộ trình có thay đổi": một dòng cho MỖI nhân viên và MỖI lần HR áp dụng một phiên bản của một ngày.

    Chi tiết từng việc đổi nằm ở `employee_task_changes`. Chuông của nhân viên đọc bảng này (đã đọc lưu ở server).
    """

    __tablename__ = "journey_change_notices"
    __table_args__ = (
        UniqueConstraint("employee_journey_id", "target_version_id"),
        Index("ix_journey_change_notices_user_id", "user_id"),
        Index("ix_journey_change_notices_target_version_id", "target_version_id"),
    )

    id: Mapped[int] = id_column()
    employee_journey_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employee_journeys.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    journey_stage_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("journey_stages.id", ondelete="SET NULL")
    )
    target_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stage_versions.id", ondelete="RESTRICT"))
    applied_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    read_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
