"""Dùng lại vector đã tính cho những đoạn không đổi giữa các phiên bản (chỉ tính embedding cho đoạn mới hoặc đã sửa).

Khóa tra cứu là **văn bản đưa vào embedding** (tiêu đề cộng nội dung) cùng **đúng phiên bản model**: cùng văn bản và cùng
model thì vector giống hệt, nên dùng lại không đổi kết quả tìm kiếm. Nguồn là chính bảng `document_chunks` của các phiên bản
khác (phiên bản bất biến, không bị xóa), tra theo chỉ mục `(content_hash, embedding_model_version)` có sẵn, nên không cần
bảng hay migration mới. Chỉ coi là trùng khi chuỗi `embedding_text` khớp **nguyên văn**, không chỉ trùng mã băm.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document_chunk import DocumentChunk
from src.services.ingest.chunker import ChunkDraft
from src.services.ingest.version_lifecycle import embedding_text_of

LOOKUP_PAGE = 500


def content_hash_of(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def find_reusable_vectors(
    session: AsyncSession,
    chunks: Sequence[ChunkDraft],
    *,
    model_version: str,
    dimension: int,
) -> dict[str, list[float]]:
    """Trả `{embedding_text: vector}` cho những đoạn đã có vector cùng model ở bất kỳ phiên bản nào."""
    wanted = {embedding_text_of(chunk) for chunk in chunks}
    hashes = sorted({content_hash_of(chunk.content) for chunk in chunks})
    found: dict[str, list[float]] = {}
    for offset in range(0, len(hashes), LOOKUP_PAGE):
        rows = await session.execute(
            select(DocumentChunk.embedding_text, DocumentChunk.embedding)
            .where(
                DocumentChunk.content_hash.in_(hashes[offset : offset + LOOKUP_PAGE]),
                DocumentChunk.embedding_model_version == model_version,
                DocumentChunk.embedding.is_not(None),
            )
            .distinct(DocumentChunk.embedding_text)
        )
        for text, vector in rows.all():
            if text in wanted and text not in found and vector is not None:
                values = [float(x) for x in vector]
                if len(values) == dimension:
                    found[text] = values
    return found
