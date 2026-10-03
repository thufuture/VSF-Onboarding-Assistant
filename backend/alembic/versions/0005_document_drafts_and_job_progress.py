"""Bản nháp tài liệu (DRAFT, parent_version_id, source) và tiến độ job (progress_percent, stage, result)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VERSION_STATUS_OLD = "'PROCESSING','PENDING_REVIEW','ACTIVE','ARCHIVED','FAILED'"
_VERSION_STATUS_NEW = "'DRAFT','PROCESSING','PENDING_REVIEW','ACTIVE','ARCHIVED','FAILED'"
_JOB_KIND_OLD = "'INGEST_VERSION','REINDEX','EMBED_RECORD','RETENTION_PURGE','INTEGRITY_CHECK'"
_JOB_KIND_NEW = "'INGEST_VERSION','ACTIVATE_VERSION','AI_TASK_PROPOSAL','REINDEX','EMBED_RECORD','RETENTION_PURGE','INTEGRITY_CHECK'"


def _swap_check(table: str, name: str, expression: str) -> None:
    op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
    op.create_check_constraint(op.f(f"ck_{table}_{name}"), table, expression)


def upgrade() -> None:
    # --- document_versions: bản nháp, nguồn gốc, khóa lạc quan ---
    op.add_column(
        "document_versions",
        sa.Column("parent_version_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_document_versions_parent_version_id_document_versions"),
        "document_versions",
        "document_versions",
        ["parent_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "document_versions",
        sa.Column("source", sa.String(length=16), server_default="UPLOAD", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_document_versions_source"), "document_versions", "source IN ('UPLOAD','EDITED')"
    )
    op.add_column("document_versions", sa.Column("updated_by", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_document_versions_updated_by_users"),
        "document_versions",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "document_versions",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    _swap_check("document_versions", "status", f"status IN ({_VERSION_STATUS_NEW})")

    # --- jobs: tiến độ, kết quả, người tạo, loại việc mới ---
    op.add_column("jobs", sa.Column("progress_percent", sa.Integer(), server_default="0", nullable=False))
    op.add_column("jobs", sa.Column("stage", sa.String(length=96), nullable=True))
    op.add_column("jobs", sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("jobs", sa.Column("created_by", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_jobs_created_by_users"), "jobs", "users", ["created_by"], ["id"], ondelete="SET NULL"
    )
    op.create_check_constraint(op.f("ck_jobs_progress_percent"), "jobs", "progress_percent BETWEEN 0 AND 100")
    _swap_check("jobs", "kind", f"kind IN ({_JOB_KIND_NEW})")
    op.create_index("ix_jobs_created_by_created_at", "jobs", ["created_by", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_created_by_created_at", table_name="jobs")
    op.execute("DELETE FROM jobs WHERE kind IN ('ACTIVATE_VERSION','AI_TASK_PROPOSAL')")
    _swap_check("jobs", "kind", f"kind IN ({_JOB_KIND_OLD})")
    op.drop_constraint(op.f("ck_jobs_progress_percent"), "jobs", type_="check")
    op.drop_constraint(op.f("fk_jobs_created_by_users"), "jobs", type_="foreignkey")
    for column in ("created_by", "result", "stage", "progress_percent"):
        op.drop_column("jobs", column)

    op.execute("DELETE FROM document_versions WHERE status = 'DRAFT'")
    _swap_check("document_versions", "status", f"status IN ({_VERSION_STATUS_OLD})")
    op.drop_column("document_versions", "updated_at")
    op.drop_constraint(op.f("fk_document_versions_updated_by_users"), "document_versions", type_="foreignkey")
    op.drop_column("document_versions", "updated_by")
    op.drop_constraint(op.f("ck_document_versions_source"), "document_versions", type_="check")
    op.drop_column("document_versions", "source")
    op.drop_constraint(
        op.f("fk_document_versions_parent_version_id_document_versions"), "document_versions", type_="foreignkey"
    )
    op.drop_column("document_versions", "parent_version_id")
