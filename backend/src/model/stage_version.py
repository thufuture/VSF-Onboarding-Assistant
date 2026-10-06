from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column
from src.model.enums import StageVersionStatus, check_in


class StageVersion(Base):
    """Một phiên bản của MỘT ngày (JourneyStage) trong Quản lý task.

    `DRAFT` sửa được; `APPLIED` là bản đang áp dụng (tối đa một bản mỗi ngày, bất biến); `ARCHIVED` là bản từng áp dụng, nay
    bị thay (không bao giờ xóa vì lộ trình của nhân viên truy về đây). Mẫu: P-040 `TemplateVersion`.
    Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md.
    """

    __tablename__ = "stage_versions"
    __table_args__ = (
        check_in("status", StageVersionStatus),
        UniqueConstraint("journey_stage_id", "version_no"),
        Index(
            "uq_stage_versions_one_applied_per_stage",
            "journey_stage_id",
            unique=True,
            postgresql_where=text("status = 'APPLIED'"),
        ),
    )

    id: Mapped[int] = id_column()
    journey_stage_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("journey_stages.id", ondelete="CASCADE"))
    version_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), server_default=StageVersionStatus.DRAFT.value)
    note: Mapped[str | None] = mapped_column(Text)
    based_on_version_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stage_versions.id", ondelete="SET NULL")
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at_column()
    applied_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    applied_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
