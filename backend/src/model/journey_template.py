from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column, updated_at_column
from src.model.enums import JourneyTemplateStatus, check_in


class JourneyTemplate(Base):
    """Portal — plan-portal/ke-hoach-trien-khai-portal.md §3, §15 v14.

    `team_id = NULL` là nội dung dùng chung (chỉ ADMIN sửa, P0A D10); publish tạo bản ghi mới
    (bất biến, xem P0A §5 retention) thay vì sửa tại chỗ — `version` tăng dần theo `code`.
    """

    __tablename__ = "journey_templates"
    __table_args__ = (check_in("status", JourneyTemplateStatus),)

    id: Mapped[int] = id_column()
    code: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), server_default=JourneyTemplateStatus.DRAFT.value)
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    published_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
