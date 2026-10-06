from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column
from src.model.enums import ReferenceStatus, check_in


class ApprovedLink(Base):
    """Link tham chiếu qua mã, kèm mô tả mục đích do content owner viết — ke-hoach-portal-onboarding.md §4.5:
    Portal/Viga không đọc/tải nội dung phía sau link, chỉ hiển thị mô tả này."""

    __tablename__ = "approved_links"
    __table_args__ = (check_in("status", ReferenceStatus),)

    id: Mapped[int] = id_column()
    code: Mapped[str] = mapped_column(String(64), unique=True)
    url: Mapped[str] = mapped_column(Text)
    purpose_note: Mapped[str] = mapped_column(Text)  # "dùng để làm gì, khi nào dùng, cần chuẩn bị gì"
    status: Mapped[str] = mapped_column(String(16), server_default=ReferenceStatus.DRAFT.value)
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
