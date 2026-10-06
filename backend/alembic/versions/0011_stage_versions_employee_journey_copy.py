"""Phiên bản theo từng ngày, lộ trình riêng (bản sao) của nhân viên, thông báo thay đổi lộ trình

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-04 09:00:00

Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md (mục 8, bước mở rộng).

- `stage_versions`: mỗi ngày có v1 (APPLIED nếu lộ trình mẫu đang PUBLISHED, ngược lại DRAFT).
- `task_templates`: thêm `stage_version_id` và `origin_key` (UUID giữ nguyên qua các phiên bản). Cột `journey_stage_id` được giữ.
- `employee_stages`, `employee_task_dependencies`: bản sao riêng của nhân viên; `employee_tasks` thêm cột nội dung riêng và đổi
  `task_template_id` thành `source_task_template_id` (cho phép NULL). Lộ trình đang có được SAO CHÉP từ mẫu hiện tại (đóng băng).
- `journey_change_notices`, `employee_task_changes`: thông báo "lộ trình có thay đổi" kèm nội dung trước và sau.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TASK_GROUPS = "'PROFILE', 'TRAINING', 'DEVICE', 'OFFICE'"


def upgrade() -> None:
    # --- 1. Phiên bản của từng ngày ---
    op.create_table(
        "stage_versions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("journey_stage_id", sa.BigInteger(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="DRAFT", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("based_on_version_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("status IN ('DRAFT', 'APPLIED', 'ARCHIVED')", name=op.f("ck_stage_versions_status")),
        sa.ForeignKeyConstraint(
            ["journey_stage_id"],
            ["journey_stages.id"],
            name=op.f("fk_stage_versions_journey_stage_id_journey_stages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["based_on_version_id"],
            ["stage_versions.id"],
            name=op.f("fk_stage_versions_based_on_version_id_stage_versions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_stage_versions_created_by_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["applied_by"], ["users.id"], name=op.f("fk_stage_versions_applied_by_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stage_versions")),
        sa.UniqueConstraint(
            "journey_stage_id", "version_no", name=op.f("uq_stage_versions_journey_stage_id_version_no")
        ),
    )
    op.create_index(
        "uq_stage_versions_one_applied_per_stage",
        "stage_versions",
        ["journey_stage_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPLIED'"),
    )
    op.execute(
        """
        INSERT INTO stage_versions (journey_stage_id, version_no, status, created_by, applied_at, applied_by)
        SELECT s.id, 1,
               CASE WHEN t.status = 'PUBLISHED' THEN 'APPLIED' ELSE 'DRAFT' END,
               t.created_by,
               CASE WHEN t.status = 'PUBLISHED' THEN COALESCE(t.published_at, now()) END,
               CASE WHEN t.status = 'PUBLISHED' THEN t.created_by END
        FROM journey_stages s
        JOIN journey_templates t ON t.id = s.journey_template_id
        """
    )

    # --- 2. Task mẫu thuộc về một phiên bản, có origin_key ---
    op.add_column("task_templates", sa.Column("stage_version_id", sa.BigInteger(), nullable=True))
    op.add_column("task_templates", sa.Column("origin_key", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE task_templates tt
        SET stage_version_id = v.id, origin_key = gen_random_uuid()
        FROM stage_versions v
        WHERE v.journey_stage_id = tt.journey_stage_id AND v.version_no = 1
        """
    )
    op.alter_column("task_templates", "stage_version_id", nullable=False)
    op.alter_column("task_templates", "origin_key", nullable=False)
    op.create_foreign_key(
        op.f("fk_task_templates_stage_version_id_stage_versions"),
        "task_templates",
        "stage_versions",
        ["stage_version_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_task_templates_stage_version_id", "task_templates", ["stage_version_id"])

    # --- 3. Bản sao riêng của nhân viên ---
    op.create_table(
        "employee_stages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("employee_journey_id", sa.BigInteger(), nullable=False),
        sa.Column("journey_stage_id", sa.BigInteger(), nullable=True),
        sa.Column("source_stage_version_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_journey_id"],
            ["employee_journeys.id"],
            name=op.f("fk_employee_stages_employee_journey_id_employee_journeys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["journey_stage_id"],
            ["journey_stages.id"],
            name=op.f("fk_employee_stages_journey_stage_id_journey_stages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_stage_version_id"],
            ["stage_versions.id"],
            name=op.f("fk_employee_stages_source_stage_version_id_stage_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_stages")),
    )
    op.create_index("ix_employee_stages_employee_journey_id", "employee_stages", ["employee_journey_id"])
    op.execute(
        """
        INSERT INTO employee_stages (employee_journey_id, journey_stage_id, source_stage_version_id, title, sort_order)
        SELECT DISTINCT et.employee_journey_id, s.id, tt.stage_version_id, s.title, s.sort_order
        FROM employee_tasks et
        JOIN task_templates tt ON tt.id = et.task_template_id
        JOIN journey_stages s ON s.id = tt.journey_stage_id
        """
    )

    op.add_column("employee_tasks", sa.Column("employee_stage_id", sa.BigInteger(), nullable=True))
    op.add_column("employee_tasks", sa.Column("origin_key", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("employee_tasks", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("employee_tasks", sa.Column("body_markdown", sa.Text(), nullable=True))
    op.add_column("employee_tasks", sa.Column("required", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("employee_tasks", sa.Column("task_group", sa.String(length=16), nullable=True))
    op.add_column("employee_tasks", sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False))
    op.execute(
        """
        UPDATE employee_tasks et
        SET employee_stage_id = es.id,
            origin_key = tt.origin_key,
            title = tt.title,
            body_markdown = tt.body_markdown,
            required = tt.required,
            task_group = tt.task_group,
            sort_order = tt.sort_order
        FROM task_templates tt, employee_stages es
        WHERE tt.id = et.task_template_id
          AND es.employee_journey_id = et.employee_journey_id
          AND es.journey_stage_id = tt.journey_stage_id
        """
    )
    op.alter_column("employee_tasks", "employee_stage_id", nullable=False)
    op.alter_column("employee_tasks", "origin_key", nullable=False)
    op.alter_column("employee_tasks", "title", nullable=False)
    op.alter_column("employee_tasks", "body_markdown", nullable=False)

    op.drop_constraint("uq_employee_tasks_employee_journey_id_task_template_id", "employee_tasks", type_="unique")
    op.drop_constraint(op.f("fk_employee_tasks_task_template_id_task_templates"), "employee_tasks", type_="foreignkey")
    op.alter_column("employee_tasks", "task_template_id", new_column_name="source_task_template_id", nullable=True)
    op.create_foreign_key(
        op.f("fk_employee_tasks_source_task_template_id_task_templates"),
        "employee_tasks",
        "task_templates",
        ["source_task_template_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_employee_tasks_employee_stage_id_employee_stages"),
        "employee_tasks",
        "employee_stages",
        ["employee_stage_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(op.f("ck_employee_tasks_task_group"), "employee_tasks", f"task_group IN ({TASK_GROUPS})")
    op.create_index(
        "uq_employee_tasks_journey_origin_key",
        "employee_tasks",
        ["employee_journey_id", "origin_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_employee_tasks_employee_stage_id", "employee_tasks", ["employee_stage_id"])

    op.create_table(
        "employee_task_dependencies",
        sa.Column("employee_task_id", sa.BigInteger(), nullable=False),
        sa.Column("depends_on_employee_task_id", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "employee_task_id <> depends_on_employee_task_id",
            name=op.f("ck_employee_task_dependencies_no_self_dependency"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_task_id"],
            ["employee_tasks.id"],
            name=op.f("fk_employee_task_dependencies_employee_task_id_employee_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["depends_on_employee_task_id"],
            ["employee_tasks.id"],
            name=op.f("fk_employee_task_dependencies_depends_on_employee_task_id_employee_tasks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "employee_task_id", "depends_on_employee_task_id", name=op.f("pk_employee_task_dependencies")
        ),
    )
    op.create_index(
        "ix_employee_task_dependencies_depends_on", "employee_task_dependencies", ["depends_on_employee_task_id"]
    )
    op.execute(
        """
        INSERT INTO employee_task_dependencies (employee_task_id, depends_on_employee_task_id)
        SELECT et.id, dep.id
        FROM task_dependencies d
        JOIN employee_tasks et ON et.source_task_template_id = d.task_template_id
        JOIN employee_tasks dep ON dep.source_task_template_id = d.depends_on_task_template_id
                               AND dep.employee_journey_id = et.employee_journey_id
        """
    )

    # --- 4. Mỗi người đúng một lộ trình chưa xóa ---
    op.execute(
        """
        UPDATE employee_journeys SET deleted_at = now()
        WHERE deleted_at IS NULL
          AND id NOT IN (SELECT max(id) FROM employee_journeys WHERE deleted_at IS NULL GROUP BY user_id)
        """
    )
    op.create_index(
        "uq_employee_journeys_one_active_per_user",
        "employee_journeys",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # --- 5. Thông báo thay đổi ---
    op.create_table(
        "journey_change_notices",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("employee_journey_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("journey_stage_id", sa.BigInteger(), nullable=True),
        sa.Column("target_version_id", sa.BigInteger(), nullable=False),
        sa.Column("applied_by", sa.BigInteger(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_journey_id"],
            ["employee_journeys.id"],
            name=op.f("fk_journey_change_notices_employee_journey_id_employee_journeys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_journey_change_notices_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["journey_stage_id"],
            ["journey_stages.id"],
            name=op.f("fk_journey_change_notices_journey_stage_id_journey_stages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_version_id"],
            ["stage_versions.id"],
            name=op.f("fk_journey_change_notices_target_version_id_stage_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applied_by"], ["users.id"], name=op.f("fk_journey_change_notices_applied_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_change_notices")),
        sa.UniqueConstraint(
            "employee_journey_id",
            "target_version_id",
            name=op.f("uq_journey_change_notices_employee_journey_id_target_version_id"),
        ),
    )
    op.create_index("ix_journey_change_notices_user_id", "journey_change_notices", ["user_id"])
    op.create_index("ix_journey_change_notices_target_version_id", "journey_change_notices", ["target_version_id"])

    op.create_table(
        "employee_task_changes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("notice_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_task_id", sa.BigInteger(), nullable=True),
        sa.Column("origin_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="PENDING", nullable=False),
        sa.Column("task_title", sa.String(length=255), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('MODIFIED', 'ADDED', 'REMOVED', 'PREREQUISITES')", name=op.f("ck_employee_task_changes_kind")
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'DISMISSED', 'SUPERSEDED')", name=op.f("ck_employee_task_changes_status")
        ),
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["journey_change_notices.id"],
            name=op.f("fk_employee_task_changes_notice_id_journey_change_notices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["employee_task_id"],
            ["employee_tasks.id"],
            name=op.f("fk_employee_task_changes_employee_task_id_employee_tasks"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_task_changes")),
    )
    op.create_index("ix_employee_task_changes_notice_id", "employee_task_changes", ["notice_id"])
    op.create_index("ix_employee_task_changes_employee_task_id", "employee_task_changes", ["employee_task_id"])


def downgrade() -> None:
    op.drop_table("employee_task_changes")
    op.drop_table("journey_change_notices")
    op.drop_index("uq_employee_journeys_one_active_per_user", table_name="employee_journeys")
    op.drop_table("employee_task_dependencies")

    # Việc không có nguồn mẫu (không thể quay về cấu trúc cũ) bị bỏ khi hạ cấp.
    op.execute("DELETE FROM employee_tasks WHERE source_task_template_id IS NULL")
    op.drop_index("ix_employee_tasks_employee_stage_id", table_name="employee_tasks")
    op.drop_index("uq_employee_tasks_journey_origin_key", table_name="employee_tasks")
    op.drop_constraint(op.f("ck_employee_tasks_task_group"), "employee_tasks", type_="check")
    op.drop_constraint(
        op.f("fk_employee_tasks_employee_stage_id_employee_stages"), "employee_tasks", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_employee_tasks_source_task_template_id_task_templates"), "employee_tasks", type_="foreignkey"
    )
    op.alter_column("employee_tasks", "source_task_template_id", new_column_name="task_template_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_employee_tasks_task_template_id_task_templates"),
        "employee_tasks",
        "task_templates",
        ["task_template_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_employee_tasks_employee_journey_id_task_template_id",
        "employee_tasks",
        ["employee_journey_id", "task_template_id"],
    )
    for column in ("sort_order", "task_group", "required", "body_markdown", "title", "origin_key", "employee_stage_id"):
        op.drop_column("employee_tasks", column)
    op.drop_table("employee_stages")

    op.drop_index("ix_task_templates_stage_version_id", table_name="task_templates")
    op.drop_constraint(op.f("fk_task_templates_stage_version_id_stage_versions"), "task_templates", type_="foreignkey")
    op.drop_column("task_templates", "origin_key")
    op.drop_column("task_templates", "stage_version_id")
    op.drop_index("uq_stage_versions_one_applied_per_stage", table_name="stage_versions")
    op.drop_table("stage_versions")
