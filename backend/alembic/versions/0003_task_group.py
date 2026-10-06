"""task_templates.task_group: nhóm task để tô màu mốc roadmap

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30 11:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("task_templates", sa.Column("task_group", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        op.f("ck_task_templates_task_group"),
        "task_templates",
        "task_group IN ('PROFILE', 'TRAINING', 'DEVICE', 'OFFICE')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_task_templates_task_group"), "task_templates", type_="check")
    op.drop_column("task_templates", "task_group")
