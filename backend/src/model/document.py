from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column, updated_at_column
from src.model.enums import Confidentiality, ContentKind, DocumentStatus, check_in


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        check_in("content_kind", ContentKind),
        check_in("confidentiality", Confidentiality),  # INV9
        check_in("status", DocumentStatus),
        Index("ix_documents_category_id", "category_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[int] = id_column()
    title: Mapped[str] = mapped_column(String(255))
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("document_categories.id", ondelete="RESTRICT"))
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    content_kind: Mapped[str] = mapped_column(String(16), server_default=ContentKind.GENERAL.value)
    confidentiality: Mapped[str] = mapped_column(String(16), server_default=Confidentiality.INTERNAL.value)
    # Định danh ổn định để nạp lại đúng tài liệu (ví dụ chinh-sach-nghi-phep-nam).
    source_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    language: Mapped[str] = mapped_column(String(8), server_default="vi")
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(16), server_default=DocumentStatus.ACTIVE.value)
    archived_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
