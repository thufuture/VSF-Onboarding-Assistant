from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column
from src.model.enums import ChangeKind, ChangeStatus, check_in


class EmployeeTaskChange(Base):
    """Một việc thay đổi trong một thông báo: nội dung TRƯỚC (của chính nhân viên) và SAU (bản mới), kèm trạng thái xử lý."""

    __tablename__ = "employee_task_changes"
    __table_args__ = (
        check_in("kind", ChangeKind),
        check_in("status", ChangeStatus),
        Index("ix_employee_task_changes_notice_id", "notice_id"),
        Index("ix_employee_task_changes_employee_task_id", "employee_task_id"),
    )

    id: Mapped[int] = id_column()
    notice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("journey_change_notices.id", ondelete="CASCADE"))
    # NULL với việc mới (chưa có trong lộ trình) hoặc khi việc đã bị dọn.
    employee_task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employee_tasks.id", ondelete="SET NULL")
    )
    origin_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(12), server_default=ChangeStatus.PENDING.value)
    task_title: Mapped[str] = mapped_column(String(255))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()
    resolved_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
