from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column


class DocumentSection(Base):
    """Parent: cả mục, nội dung nguyên văn đưa cho LLM và là nơi validator kiểm quote (INV13)."""

    __tablename__ = "document_sections"
    __table_args__ = (UniqueConstraint("version_id", "section_index"),)  # INV14

    id: Mapped[int] = id_column()
    version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("document_versions.id", ondelete="RESTRICT"))
    section_index: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(Text)
    section_path: Mapped[str | None] = mapped_column(Text)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()
