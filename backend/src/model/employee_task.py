from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column
from src.model.enums import EmployeeTaskStatus, TaskGroup, check_in


class EmployeeTask(Base):
    """Một việc trong lộ trình RIÊNG của nhân viên — BẢN SAO độc lập (P-040 `PlanTask`).

    Tên, nội dung, bắt buộc, nhóm, thứ tự nằm ngay ở đây; sửa hay áp dụng bản mới ở Quản lý task KHÔNG đổi các cột này,
    chỉ đổi khi chính nhân viên bấm "Cập nhật" (journey_change_notices). `source_task_template_id` chỉ để truy nguồn
    (trích dẫn tài liệu cho Viga và "xem đúng đoạn nguồn"); NULL nếu việc không có nguồn mẫu.

    P0A D1: hoàn thành là 1 hành động duy nhất cho cả task (không sub-step, không duyệt); `completed_at` set khi nhân viên tự bấm
    "Hoàn thành". `status` tính bằng code từ `employee_task_dependencies` (chỉ AND — P0A D8), không phải người dùng tự chọn.
    """

    __tablename__ = "employee_tasks"
    __table_args__ = (
        check_in("status", EmployeeTaskStatus),
        check_in("task_group", TaskGroup),
        Index(
            "uq_employee_tasks_journey_origin_key",
            "employee_journey_id",
            "origin_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_employee_tasks_team_id", "team_id"),
        Index("ix_employee_tasks_status", "status"),
        Index("ix_employee_tasks_employee_stage_id", "employee_stage_id"),
    )

    id: Mapped[int] = id_column()
    employee_journey_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employee_journeys.id", ondelete="CASCADE"))
    employee_stage_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employee_stages.id", ondelete="CASCADE"))
    source_task_template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_templates.id", ondelete="RESTRICT")
    )
    origin_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    title: Mapped[str] = mapped_column(String(255))
    body_markdown: Mapped[str] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(server_default="true")
    task_group: Mapped[str | None] = mapped_column(String(16))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20), server_default=EmployeeTaskStatus.LOCKED.value)
    completed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    deleted_at: Mapped[datetime | None] = mapped_column(TimestampTZ)  # soft delete — P0A §5 retention
    created_at: Mapped[datetime] = created_at_column()
