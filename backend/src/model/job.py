from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column
from src.model.enums import JobKind, JobStatus, check_in


class Job(Base):
    """Hàng đợi công việc nền bằng Postgres (worker lấy bằng FOR UPDATE SKIP LOCKED)."""

    __tablename__ = "jobs"
    __table_args__ = (
        check_in("kind", JobKind),
        check_in("status", JobStatus),
        # INV10: không hai job cùng khóa chạy chồng.
        Index(
            "uq_jobs_active_idempotency",
            "idempotency_key",
            unique=True,
            postgresql_where=text("status IN ('PENDING','RUNNING')"),
        ),
        Index("ix_jobs_status_run_after", "status", "run_after"),
        Index("ix_jobs_created_by_created_at", "created_by", "created_at"),
        CheckConstraint("progress_percent BETWEEN 0 AND 100", name="progress_percent"),
    )

    id: Mapped[int] = id_column()
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), server_default=JobStatus.PENDING.value)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("3"))
    run_after: Mapped[datetime] = mapped_column(TimestampTZ, server_default=func.now())
    locked_by: Mapped[str | None] = mapped_column(String(64))
    locked_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    document_version_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("document_versions.id", ondelete="SET NULL")
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    # Tiến độ cho giao diện (không chứa nội dung tài liệu, INV8) và kết quả cuối (vd. danh sách đề xuất task).
    progress_percent: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    stage: Mapped[str | None] = mapped_column(String(96))
    # Tiến độ theo bước (mục 13 của kế hoạch tối ưu): các bước, trạng thái, số đếm, thời điểm. Chỉ mã bước và số, không nội dung (INV8).
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created_at_column()
    started_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    finished_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
