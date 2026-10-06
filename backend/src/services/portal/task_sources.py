"""Nguồn tài liệu của task: tài liệu, mục và đoạn trích nguyên văn (nút "Nguồn" trên task của HR và nhân viên).

`task_source_mappings` giữ mục (`document_section_id`) và đoạn trích (`quote`). Giao diện mở tài liệu tại đúng mục và tô đúng
đoạn trích; task cũ chưa có `quote` thì chỉ tô cả mục.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document import Document
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.task_source_mapping import TaskSourceMapping


@dataclass(frozen=True)
class TaskSource:
    document_title: str
    version_label: str
    version_id: int
    document_url: str
    section_heading: str | None
    quote: str | None


async def sources_by_task(session: AsyncSession, task_template_ids: Iterable[int]) -> dict[int, list[TaskSource]]:
    """`task_template_id -> các nguồn`, theo thứ tự ghi nhận; task không có nguồn thì không có khóa."""
    ids = sorted(set(task_template_ids))
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(
                TaskSourceMapping.task_template_id,
                Document.title,
                DocumentVersion.version_label,
                DocumentVersion.id,
                DocumentVersion.storage_key,
                DocumentSection.heading,
                TaskSourceMapping.quote,
            )
            .join(DocumentVersion, DocumentVersion.id == TaskSourceMapping.document_version_id)
            .join(Document, Document.id == TaskSourceMapping.document_id)
            .outerjoin(DocumentSection, DocumentSection.id == TaskSourceMapping.document_section_id)
            .where(TaskSourceMapping.task_template_id.in_(ids))
            .order_by(TaskSourceMapping.task_template_id, TaskSourceMapping.id)
        )
    ).all()
    result: dict[int, list[TaskSource]] = {}
    for task_id, title, label, version_id, storage_key, heading, quote in rows:
        result.setdefault(task_id, []).append(
            TaskSource(
                document_title=title,
                version_label=label,
                version_id=version_id,
                document_url=storage_key,
                section_heading=heading,
                quote=quote,
            )
        )
    return result
