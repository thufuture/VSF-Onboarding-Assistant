"""Ảnh và video đính kèm ticket (file trên Cloudinary, DB giữ URL)

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-05 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_attachments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("uploaded_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_message_id", sa.BigInteger(), nullable=True),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_ticket_attachments_uploaded_by_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_message_id"],
            ["ticket_messages.id"],
            name=op.f("fk_ticket_attachments_ticket_message_id_ticket_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_attachments")),
    )
    op.create_index("ix_ticket_attachments_ticket_message_id", "ticket_attachments", ["ticket_message_id"])
    op.create_index(
        "ix_ticket_attachments_uploader_pending", "ticket_attachments", ["uploaded_by_user_id", "ticket_message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_attachments_uploader_pending", table_name="ticket_attachments")
    op.drop_index("ix_ticket_attachments_ticket_message_id", table_name="ticket_attachments")
    op.drop_table("ticket_attachments")
