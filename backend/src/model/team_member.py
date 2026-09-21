from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column


class TeamMember(Base):
    __tablename__ = "team_members"
    # Xác định người xử lý của hàng đợi theo người dùng.
    __table_args__ = (Index("ix_team_members_user_id", "user_id"),)

    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="RESTRICT"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = created_at_column()
