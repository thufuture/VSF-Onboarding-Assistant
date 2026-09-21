from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column
from src.model.enums import VersionStatus, check_in


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        check_in("status", VersionStatus),
        # INV5: cùng nhãn phiên bản không có nội dung khác.
        UniqueConstraint("document_id", "version_label"),
        UniqueConstraint("document_id", "revision_no"),
        # INV12: ngày hiệu lực hợp lệ.
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="effective_dates_valid",
        ),
        # INV1: các bản ACTIVE của một tài liệu không chồng khoảng hiệu lực. Ngày trống = không giới hạn.
        ExcludeConstraint(
            ("document_id", "="),
            (text("daterange(effective_from, effective_to, '[]')"), "&&"),
            using="gist",
            where=text("status = 'ACTIVE'"),
            name="active_no_overlap",
        ),
        Index("ix_document_versions_status", "status"),
        Index("ix_document_versions_content_checksum", "content_checksum"),
    )

    id: Mapped[int] = id_column()
    document_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("documents.id", ondelete="RESTRICT"))
    version_label: Mapped[str] = mapped_column(String(32))
    # Tăng đơn điệu theo tài liệu.
    revision_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), server_default=VersionStatus.PROCESSING.value)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(Text)
    file_checksum: Mapped[str] = mapped_column(String(64))
    # sha256 của Markdown đã che secret: cơ sở của INV5 và idempotency ingest.
    content_checksum: Mapped[str] = mapped_column(String(64))
    page_count: Mapped[int | None] = mapped_column(Integer)
    parser: Mapped[str] = mapped_column(String(32))
    markdown: Mapped[str] = mapped_column(Text)
    quality_report: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    # Gợi ý tìm kiếm, không bao giờ là nguồn trích dẫn (INV13).
    summary: Mapped[str | None] = mapped_column(Text)
    sample_questions: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    effective_from: Mapped[date | None]
    effective_to: Mapped[date | None]
    embedding_model_version: Mapped[str] = mapped_column(String(64))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    activated_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_at: Mapped[datetime] = created_at_column()
