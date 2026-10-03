"""Đánh giá 👍/👎 cho câu trả lời Viga, đoạn trích của task, ngữ cảnh cho câu chưa trả lời được

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-02 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("task_source_mappings", sa.Column("quote", sa.Text(), nullable=True))

    op.add_column("content_gaps", sa.Column("kind", sa.String(length=12), server_default="NO_BASIS", nullable=False))
    op.add_column("content_gaps", sa.Column("answer_excerpt", sa.Text(), nullable=True))
    op.add_column("content_gaps", sa.Column("resolved_by_version_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_content_gaps_resolved_by_version_id_document_versions"),
        "content_gaps",
        "document_versions",
        ["resolved_by_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "viga_feedback",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.BigInteger(), nullable=True),
        sa.Column("rating", sa.String(length=8), nullable=False),
        sa.Column("reason", sa.String(length=24), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating IN ('UP', 'DOWN')", name=op.f("ck_viga_feedback_rating")),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_viga_feedback_message_id_chat_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_viga_feedback_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_viga_feedback_team_id_teams"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_viga_feedback")),
        sa.UniqueConstraint("message_id", name="uq_viga_feedback_message_id"),
    )
    op.create_index("ix_viga_feedback_team_id_rating", "viga_feedback", ["team_id", "rating"])


def downgrade() -> None:
    op.drop_index("ix_viga_feedback_team_id_rating", table_name="viga_feedback")
    op.drop_table("viga_feedback")
    op.drop_constraint(
        op.f("fk_content_gaps_resolved_by_version_id_document_versions"), "content_gaps", type_="foreignkey"
    )
    op.drop_column("content_gaps", "resolved_by_version_id")
    op.drop_column("content_gaps", "answer_excerpt")
    op.drop_column("content_gaps", "kind")
    op.drop_column("task_source_mappings", "quote")
