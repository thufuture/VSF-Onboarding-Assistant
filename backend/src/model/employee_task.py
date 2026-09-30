from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column
from src.model.enums import EmployeeTaskStatus, check_in


class EmployeeTask(Base):
    """Portal — P0A D1: hoàn thành là 1 hành động duy nhất cho cả task (không có sub-step, không có
    duyệt/minh chứng); `completed_at` set khi nhân viên tự bấm "Hoàn thành". `status` tính bằng code từ
    `task_dependencies` (chỉ AND — P0A D8), không phải người dùng tự chọn."""

    __tablename__ = "employee_tasks"
    __table_args__ = (
        check_in("status", EmployeeTaskStatus),
        UniqueConstraint("employee_journey_id", "task_template_id"),
        Index("ix_employee_tasks_team_id", "team_id"),
        Index("ix_employee_tasks_status", "status"),
    )

    id: Mapped[int] = id_column()
    employee_journey_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employee_journeys.id", ondelete="CASCADE"))
    task_template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_templates.id", ondelete="RESTRICT"))
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20), server_default=EmployeeTaskStatus.LOCKED.value)
    completed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    deleted_at: Mapped[datetime | None] = mapped_column(TimestampTZ)  # soft delete — P0A §5 retention
    created_at: Mapped[datetime] = created_at_column()
