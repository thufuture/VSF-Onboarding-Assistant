from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column


class JourneyStage(Base):
    __tablename__ = "journey_stages"
    __table_args__ = (Index("ix_journey_stages_journey_template_id", "journey_template_id"),)

    id: Mapped[int] = id_column()
    journey_template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("journey_templates.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = created_at_column()
