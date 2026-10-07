"""Thông báo lộ trình: đánh dấu ngày mới (nhân viên chưa có ngày đó)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-07 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "journey_change_notices",
        sa.Column("new_stage", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("journey_change_notices", "new_stage")
