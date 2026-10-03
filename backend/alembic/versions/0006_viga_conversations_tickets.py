"""Viga: hội thoại lưu trên máy chủ, ghi "việc vừa mở", nguồn và hội thoại gốc của ticket

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-01 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_chat_conversations_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_conversations")),
    )
    op.create_index("ix_chat_conversations_user_id_updated_at", "chat_conversations", ["user_id", "updated_at"])
    op.create_index("ix_chat_conversations_updated_at", "chat_conversations", ["updated_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("response_type", sa.String(length=32), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('USER','ASSISTANT')", name=op.f("ck_chat_messages_role")),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.id"],
            name=op.f("fk_chat_messages_conversation_id_chat_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index("ix_chat_messages_conversation_id_id", "chat_messages", ["conversation_id", "id"])

    op.add_column("employee_journeys", sa.Column("last_opened_task_id", sa.BigInteger(), nullable=True))
    op.add_column("employee_journeys", sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_employee_journeys_last_opened_task_id_employee_tasks"),
        "employee_journeys",
        "employee_tasks",
        ["last_opened_task_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("tickets", sa.Column("source", sa.String(length=8), server_default="MANUAL", nullable=False))
    op.create_check_constraint(op.f("ck_tickets_source"), "tickets", "source IN ('MANUAL','VIGA')")
    op.add_column("tickets", sa.Column("conversation_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_tickets_conversation_id_chat_conversations"),
        "tickets",
        "chat_conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tickets_created_by_user_id_created_at", "tickets", ["created_by_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_tickets_created_by_user_id_created_at", table_name="tickets")
    op.drop_constraint(op.f("fk_tickets_conversation_id_chat_conversations"), "tickets", type_="foreignkey")
    op.drop_column("tickets", "conversation_id")
    op.drop_constraint(op.f("ck_tickets_source"), "tickets", type_="check")
    op.drop_column("tickets", "source")

    op.drop_constraint(
        op.f("fk_employee_journeys_last_opened_task_id_employee_tasks"), "employee_journeys", type_="foreignkey"
    )
    op.drop_column("employee_journeys", "last_opened_at")
    op.drop_column("employee_journeys", "last_opened_task_id")

    op.drop_index("ix_chat_messages_conversation_id_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_conversations_updated_at", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_user_id_updated_at", table_name="chat_conversations")
    op.drop_table("chat_conversations")
