"""llm_calls.job_id: cộng chi phí và độ trễ theo từng lượt việc nền (tạo task bằng AI, kích hoạt tài liệu)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-01 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("llm_calls", sa.Column("job_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_llm_calls_job_id", "llm_calls", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_job_id", table_name="llm_calls")
    op.drop_column("llm_calls", "job_id")
