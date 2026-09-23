"""Nạp `document_categories` từ `registry/document_categories.json`. Dùng lại được ở mọi môi trường
(không phải dữ liệu dev, không có nhánh chặn production như `seed_users`) — danh mục là dữ liệu nghiệp
vụ thật (HR quản lý ở Phase 5), chỉ đang gieo trước từ registry cho tiện thử nghiệm 2-B.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document_category import DocumentCategory


@dataclass
class CategorySeedReport:
    created: int = 0


async def seed_document_categories(session: AsyncSession, registry_dir: Path) -> CategorySeedReport:
    items = cast(list[dict[str, Any]], json.loads((registry_dir / "document_categories.json").read_text("utf-8")))
    report = CategorySeedReport()
    for index, item in enumerate(items):
        existing = await session.scalar(select(DocumentCategory).where(DocumentCategory.slug == item["slug"]))
        if existing is None:
            session.add(
                DocumentCategory(
                    slug=item["slug"],
                    name=item["name"],
                    description=item.get("description"),
                    sort_order=index,
                )
            )
            report.created += 1
    await session.commit()
    return report
