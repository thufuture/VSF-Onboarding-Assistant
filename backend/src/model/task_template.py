from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column
from src.model.enums import TaskGroup, check_in


class TaskTemplate(Base):
    """Portal — không có `completion_type`/`applies_when` (P0A D1, D3, D4): mọi task chỉ tự-hoàn-thành;
    khác biệt theo địa điểm/loại máy viết trực tiếp trong `body_markdown`.

    Task thuộc về MỘT phiên bản của một ngày (`stage_version_id`). `journey_stage_id` giữ nguyên bằng ngày của phiên bản đó
    (cột dư để các truy vấn cũ vẫn chạy). `origin_key` giữ nguyên khi sao chép phiên bản: một việc ở v1, v2, v3 cùng một mã,
    dùng để so "trước và sau" giữa các phiên bản và khớp việc trong lộ trình của nhân viên.
    """

    __tablename__ = "task_templates"
    __table_args__ = (
        check_in("task_group", TaskGroup),
        Index("ix_task_templates_journey_stage_id", "journey_stage_id"),
        Index("ix_task_templates_stage_version_id", "stage_version_id"),
        Index("ix_task_templates_team_id", "team_id"),
    )

    id: Mapped[int] = id_column()
    journey_stage_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("journey_stages.id", ondelete="CASCADE"))
    stage_version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stage_versions.id", ondelete="CASCADE"))
    origin_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), default=uuid4)
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
