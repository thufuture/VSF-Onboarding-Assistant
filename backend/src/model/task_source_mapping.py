from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, id_column


class TaskSourceMapping(Base):
    """Nối 1 TaskTemplate với đúng tài liệu/section đã ingest — dùng cho AI đề xuất task và trích dẫn,
    không nạp lại RAG riêng cho Portal (tái dùng `documents`/`document_versions`/`document_sections`)."""

    __tablename__ = "task_source_mappings"
    __table_args__ = (Index("ix_task_source_mappings_document_id", "document_id"),)

    id: Mapped[int] = id_column()
    task_template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_templates.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("documents.id", ondelete="RESTRICT"))
    document_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("document_versions.id", ondelete="RESTRICT")
    )
    document_section_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("document_sections.id", ondelete="RESTRICT")
    )
