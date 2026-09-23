"""Đọc dữ liệu nền từ registry (mục 7, kế hoạch 2-B): danh mục tài liệu, người "chủ sở hữu" (FK
`owner_id`/`uploaded_by`), và một dòng của `manifests/documents_manifest.csv` để lấy sẵn metadata
(tiêu đề, danh mục, nhãn phiên bản, ngày hiệu lực...) — không cần nhập tay khi nạp dữ liệu giả lập.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document_category import DocumentCategory
from src.model.user import User


class RegistryLookupError(Exception):
    """Không tìm thấy danh mục/người dùng/dòng manifest cần thiết."""


async def get_category_by_slug(session: AsyncSession, slug: str) -> DocumentCategory:
    category = await session.scalar(select(DocumentCategory).where(DocumentCategory.slug == slug))
    if category is None:
        raise RegistryLookupError(
            f"chưa có danh mục '{slug}' trong document_categories — chạy "
            "`python -m src.cli.seed_document_categories` trước"
        )
    return category


async def get_user_by_email(session: AsyncSession, email: str) -> User:
    normalized = email.strip().lower()
    user = await session.scalar(select(User).where(func.lower(User.email) == normalized))
    if user is None:
        raise RegistryLookupError(f"không tìm thấy người dùng '{email}' — chạy `python -m src.cli.seed_users` trước")
    return user


@dataclass(frozen=True)
class ManifestRow:
    id: str
    file: str
    relative_path: str
    title: str
    source_key: str
    category_slug: str
    version_label: str
    effective_from: str
    content_kind: str
    confidentiality: str


def read_manifest_row(manifest_path: Path, document_id: str) -> ManifestRow:
    with manifest_path.open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["id"] == document_id:
                return ManifestRow(
                    id=row["id"],
                    file=row["file"],
                    relative_path=row["relative_path"],
                    title=row["title"],
                    source_key=row["series"],
                    category_slug=row["category"],
                    version_label=row["version_label"],
                    effective_from=row["effective_from"],
                    content_kind=row["content_kind"],
                    confidentiality=row["confidentiality"],
                )
    raise RegistryLookupError(f"không tìm thấy '{document_id}' trong {manifest_path}")
