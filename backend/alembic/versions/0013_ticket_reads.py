"""Mốc đã xem ticket của từng người (để đếm ticket có tin chưa đọc)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-05 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_reads",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("last_read_message_id", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name=op.f("fk_ticket_reads_ticket_id_tickets"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_ticket_reads_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("ticket_id", "user_id", name=op.f("pk_ticket_reads")),
    )


def downgrade() -> None:
    op.drop_table("ticket_reads")
