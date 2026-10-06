from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base


class TaskDependency(Base):
    """Prerequisite giữa 2 TaskTemplate. Chỉ AND — P0A D8: task chỉ READY khi TOÀN BỘ dòng ở đây trỏ
    tới task đã DONE. Không có OR/nhóm thay thế ở MVP (thêm bảng riêng sau nếu cần, không sửa bảng này)."""

    __tablename__ = "task_dependencies"
    __table_args__ = (
        CheckConstraint("task_template_id <> depends_on_task_template_id", name="no_self_dependency"),
        Index("ix_task_dependencies_depends_on", "depends_on_task_template_id"),
    )

    task_template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_templates.id", ondelete="CASCADE"), primary_key=True
    )
    depends_on_task_template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("task_templates.id", ondelete="CASCADE"), primary_key=True
    )
