from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base


class EmployeeTaskDependency(Base):
    """Tiên quyết (chỉ AND) giữa hai việc trong lộ trình RIÊNG của nhân viên; thay cho đọc `task_dependencies` của mẫu."""

    __tablename__ = "employee_task_dependencies"
    __table_args__ = (
        CheckConstraint("employee_task_id <> depends_on_employee_task_id", name="no_self_dependency"),
        Index("ix_employee_task_dependencies_depends_on", "depends_on_employee_task_id"),
    )

    employee_task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employee_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    depends_on_employee_task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employee_tasks.id", ondelete="CASCADE"), primary_key=True
    )
