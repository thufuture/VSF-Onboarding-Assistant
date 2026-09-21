from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import EMBEDDING_DIMENSION, Base, created_at_column, id_column


class DocumentChunk(Base):
    """Child (~256 token): được embed và đánh chỉ mục BM25 để tìm; nội dung hiển thị lấy từ parent."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("version_id", "chunk_index"),  # INV14
        Index("ix_document_chunks_section_id", "section_id"),
        # Tra cache embedding theo lô.
        Index("ix_document_chunks_content_hash_embedding_model_version", "content_hash", "embedding_model_version"),
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # BM25 của ParadeDB (pg_search). key_field bắt buộc.
        Index(
            "ix_document_chunks_bm25",
            "id",
            "lexical_text",
            "heading",
            postgresql_using="bm25",
            postgresql_with={"key_field": "'id'"},
        ),
    )

    id: Mapped[int] = id_column()
    section_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("document_sections.id", ondelete="RESTRICT"))
    # Phi chuẩn hóa để lọc hiệu lực nhanh; service kiểm chunk.version_id = section.version_id (INV14).
    version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("document_versions.id", ondelete="RESTRICT"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(Text)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    anchor: Mapped[str | None] = mapped_column(Text)
    # Nguyên văn, dùng để hiển thị và trích dẫn.
    content: Mapped[str] = mapped_column(Text)
    # Tiền tố + gợi ý tìm kiếm + nội dung, đưa vào embedding.
    embedding_text: Mapped[str] = mapped_column(Text)
    # Văn bản đã tách từ tiếng Việt cho BM25.
    lexical_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column(Integer)
    embedding_model_version: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION))
    created_at: Mapped[datetime] = created_at_column()
