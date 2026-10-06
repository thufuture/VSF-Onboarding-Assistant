"""Số đo từng pha của lời gọi LLM (llm_calls) và tiến độ theo bước của việc nền (jobs.progress)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-03 10:00:00

Chỉ thêm cột (cho phép rỗng hoặc có mặc định) nên chạy lại hay quay lại đều an toàn; không chứa nội dung tài liệu (INV8).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("llm_calls", sa.Column("first_byte_ms", sa.Float(), nullable=True))
    op.add_column("llm_calls", sa.Column("first_token_ms", sa.Float(), nullable=True))
    op.add_column("llm_calls", sa.Column("reasoning_ms", sa.Float(), nullable=True))
    op.add_column("llm_calls", sa.Column("content_ms", sa.Float(), nullable=True))
    op.add_column("llm_calls", sa.Column("reasoning_tokens", sa.Integer(), server_default="0", nullable=False))
    op.add_column("llm_calls", sa.Column("cached_input_tokens", sa.Integer(), server_default="0", nullable=False))
    op.add_column("llm_calls", sa.Column("finish_reason", sa.String(length=16), nullable=True))
    op.add_column("llm_calls", sa.Column("attempt", sa.Integer(), server_default="1", nullable=False))
    op.add_column("llm_calls", sa.Column("queue_wait_ms", sa.Float(), nullable=True))
    op.add_column("jobs", sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "progress")
    for column in (
        "queue_wait_ms",
        "attempt",
        "finish_reason",
        "cached_input_tokens",
        "reasoning_tokens",
        "content_ms",
        "reasoning_ms",
        "first_token_ms",
        "first_byte_ms",
    ):
        op.drop_column("llm_calls", column)
