"""core: extension, người dùng, đội, tài liệu (phiên bản, section, chunk), job, nhật ký kiểm toán

Revision ID: 0001
Revises:
Create Date: 2026-09-21 12:09:52.537693

Viết đầy đủ một lần ở Phase 2 (database-design mục 7). Không sửa sau khi đã áp dụng: thay đổi về sau là migration mới.
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # vector và pg_search có sẵn trong image ParadeDB; btree_gist cần cho EXCLUDE USING gist theo khoảng ngày.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "document_categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_document_categories_slug")),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ticket_prefix", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        sa.UniqueConstraint("code", name=op.f("uq_teams_code")),
        sa.UniqueConstraint("ticket_prefix", name=op.f("uq_teams_ticket_prefix")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="USER", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="ACTIVE", nullable=False),
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("session_invalid_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('USER', 'HR', 'ADMIN')", name=op.f("ck_users_role")),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name=op.f("ck_users_status")),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_users_created_by_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index("uq_users_lower_email", "users", [sa.literal_column("lower(email)")], unique=True)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trace_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_logs_actor_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("content_kind", sa.String(length=16), server_default="GENERAL", nullable=False),
        sa.Column("confidentiality", sa.String(length=16), server_default="INTERNAL", nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=8), server_default="vi", nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="ACTIVE", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidentiality IN ('PUBLIC', 'INTERNAL')", name=op.f("ck_documents_confidentiality")),
        sa.CheckConstraint("content_kind IN ('GENERAL', 'PROCEDURE_GUIDE')", name=op.f("ck_documents_content_kind")),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name=op.f("ck_documents_status")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["document_categories.id"],
            name=op.f("fk_documents_category_id_document_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_documents_owner_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("source_key", name=op.f("uq_documents_source_key")),
    )
    op.create_index("ix_documents_category_id", "documents", ["category_id"], unique=False)
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)
    op.create_index("ix_documents_tags", "documents", ["tags"], unique=False, postgresql_using="gin")
    op.create_table(
        "team_members",
        sa.Column("team_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_team_members_team_id_teams"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_team_members_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("team_id", "user_id", name=op.f("pk_team_members")),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"], unique=False)
    op.create_table(
        "document_versions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("version_label", sa.String(length=32), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PROCESSING", nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("file_checksum", sa.String(length=64), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("parser", sa.String(length=32), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column(
            "quality_report",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("sample_questions", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("embedding_model_version", sa.String(length=64), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        postgresql.ExcludeConstraint(
            (sa.column("document_id"), "="),
            (sa.text("daterange(effective_from, effective_to, '[]')"), "&&"),
            where=sa.text("status = 'ACTIVE'"),
            using="gist",
            name=op.f("ex_document_versions_active_no_overlap"),
        ),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'PENDING_REVIEW', 'ACTIVE', 'ARCHIVED', 'FAILED')",
            name=op.f("ck_document_versions_status"),
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name=op.f("ck_document_versions_effective_dates_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_versions_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], name=op.f("fk_document_versions_reviewed_by_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"], ["users.id"], name=op.f("fk_document_versions_uploaded_by_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        sa.UniqueConstraint("document_id", "revision_no", name=op.f("uq_document_versions_document_id_revision_no")),
        sa.UniqueConstraint(
            "document_id", "version_label", name=op.f("uq_document_versions_document_id_version_label")
        ),
    )
    op.create_index("ix_document_versions_content_checksum", "document_versions", ["content_checksum"], unique=False)
    op.create_index("ix_document_versions_status", "document_versions", ["status"], unique=False)
    op.create_table(
        "document_sections",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("version_id", sa.BigInteger(), nullable=False),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("section_path", sa.Text(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_sections_version_id_document_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_sections")),
        sa.UniqueConstraint("version_id", "section_index", name=op.f("uq_document_sections_version_id_section_index")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_version_id", sa.BigInteger(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('INGEST_VERSION', 'REINDEX', 'EMBED_RECORD', 'RETENTION_PURGE', 'INTEGRITY_CHECK')",
            name=op.f("ck_jobs_kind"),
        ),
        sa.CheckConstraint("status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')", name=op.f("ck_jobs_status")),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name=op.f("fk_jobs_document_version_id_document_versions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_status_run_after", "jobs", ["status", "run_after"], unique=False)
    op.create_index(
        "uq_jobs_active_idempotency",
        "jobs",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','RUNNING')"),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("section_id", sa.BigInteger(), nullable=False),
        sa.Column("version_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("anchor", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("lexical_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding_model_version", sa.String(length=64), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["document_sections.id"],
            name=op.f("fk_document_chunks_section_id_document_sections"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_chunks_version_id_document_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint("version_id", "chunk_index", name=op.f("uq_document_chunks_version_id_chunk_index")),
    )
    op.create_index(
        "ix_document_chunks_bm25",
        "document_chunks",
        ["id", "lexical_text", "heading"],
        unique=False,
        postgresql_using="bm25",
        postgresql_with={"key_field": "'id'"},
    )
    op.create_index(
        "ix_document_chunks_content_hash_embedding_model_version",
        "document_chunks",
        ["content_hash", "embedding_model_version"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_embedding",
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_document_chunks_section_id", "document_chunks", ["section_id"], unique=False)


def downgrade() -> None:
    # Extension giữ nguyên (image đã cài sẵn; xóa có thể ảnh hưởng dữ liệu khác).
    op.drop_index("ix_document_chunks_section_id", table_name="document_chunks")
    op.drop_index(
        "ix_document_chunks_embedding",
        table_name="document_chunks",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index("ix_document_chunks_content_hash_embedding_model_version", table_name="document_chunks")
    op.drop_index(
        "ix_document_chunks_bm25",
        table_name="document_chunks",
        postgresql_using="bm25",
        postgresql_with={"key_field": "'id'"},
    )
    op.drop_table("document_chunks")
    op.drop_index(
        "uq_jobs_active_idempotency", table_name="jobs", postgresql_where=sa.text("status IN ('PENDING','RUNNING')")
    )
    op.drop_index("ix_jobs_status_run_after", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("document_sections")
    op.drop_index("ix_document_versions_status", table_name="document_versions")
    op.drop_index("ix_document_versions_content_checksum", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("ix_documents_tags", table_name="documents", postgresql_using="gin")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_category_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_audit_logs_entity_type_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("uq_users_lower_email", table_name="users")
    op.drop_table("users")
    op.drop_table("teams")
    op.drop_table("document_categories")
