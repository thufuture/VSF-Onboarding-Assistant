from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column
from src.model.enums import ReferenceStatus, check_in


class ContactChannel(Base):
    """Đầu mối tham chiếu qua mã — ke-hoach-portal-onboarding.md §4.3: task chỉ chứa `code`, giá trị thật
    (tên, email...) nằm ở đây, chỉ hiển thị khi `status = APPROVED`."""

    __tablename__ = "contact_channels"
    __table_args__ = (check_in("status", ReferenceStatus),)

    id: Mapped[int] = id_column()
    code: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(255))
    value: Mapped[str | None] = mapped_column(Text)  # email/tên người phụ trách... để trống khi còn DRAFT
    status: Mapped[str] = mapped_column(String(16), server_default=ReferenceStatus.DRAFT.value)
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
