"""Danh mục tài liệu của Portal chỉ còn hai nhóm: Onboarding và Tài liệu khác

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-02 10:00:00

Chỉ đổi dữ liệu: thêm hai danh mục, chuyển tài liệu sang đó (tài liệu thuộc "Onboarding và ngày đầu" về Onboarding, còn lại về
Tài liệu khác) rồi ẩn các danh mục cũ (không xóa để các bản ghi lịch sử và công cụ nạp bằng dòng lệnh vẫn tham chiếu được).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEEP = ("onboarding", "tai-lieu-khac")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO document_categories (slug, name, description, sort_order, is_active) VALUES "
            "('onboarding', 'Onboarding', 'Tài liệu cho nhân sự mới: ngày đầu, giấy tờ, lịch tuần đầu, thiết bị, quy định cần biết', 1, true), "
            "('tai-lieu-khac', 'Tài liệu khác', 'Các tài liệu còn lại', 2, true) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, "
            "sort_order = EXCLUDED.sort_order, is_active = true"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE documents SET category_id = (SELECT id FROM document_categories WHERE slug = 'onboarding') "
            "WHERE category_id IN (SELECT id FROM document_categories WHERE slug = 'onboarding-ngay-dau')"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE documents SET category_id = (SELECT id FROM document_categories WHERE slug = 'tai-lieu-khac') "
            "WHERE category_id IN (SELECT id FROM document_categories WHERE slug NOT IN ('onboarding', 'tai-lieu-khac'))"
        )
    )
    bind.execute(
        sa.text("UPDATE document_categories SET is_active = false WHERE slug NOT IN ('onboarding', 'tai-lieu-khac')")
    )


def downgrade() -> None:
    # Bật lại các danh mục cũ; tài liệu đã chuyển nhóm giữ nguyên ở hai nhóm mới.
    op.get_bind().execute(
        sa.text("UPDATE document_categories SET is_active = true WHERE slug NOT IN ('onboarding', 'tai-lieu-khac')")
    )
