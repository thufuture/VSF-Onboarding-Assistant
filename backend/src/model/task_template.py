from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column
from src.model.enums import TaskGroup, check_in


class TaskTemplate(Base):
    """Portal — không có `completion_type`/`applies_when` (P0A D1, D3, D4): mọi task chỉ tự-hoàn-thành;
    khác biệt theo địa điểm/loại máy viết trực tiếp trong `body_markdown`."""

    __tablename__ = "task_templates"
    __table_args__ = (
        check_in("task_group", TaskGroup),
        Index("ix_task_templates_journey_stage_id", "journey_stage_id"),
        Index("ix_task_templates_team_id", "team_id"),
    )

    id: Mapped[int] = id_column()
    journey_stage_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("journey_stages.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    body_markdown: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    required: Mapped[bool] = mapped_column(server_default="true")
    # NULL = chưa phân nhóm; giao diện tô màu mốc theo nhóm này.
    task_group: Mapped[str | None] = mapped_column(String(16))
    # NULL = dùng chung toàn công ty (P0A D10); chỉ ADMIN sửa được ở tầng ứng dụng.
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
