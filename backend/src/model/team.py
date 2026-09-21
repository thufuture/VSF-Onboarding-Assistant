from datetime import datetime

from sqlalchemy import String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = id_column()
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    ticket_prefix: Mapped[str | None] = mapped_column(String(8), unique=True)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
