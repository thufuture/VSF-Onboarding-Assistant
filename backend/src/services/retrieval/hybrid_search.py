"""Tìm kiếm hybrid trên `document_chunks`: BM25 (`pg_search`, toán tử `@@@`) + dense (`pgvector`, `<=>`),
hợp nhất bằng Reciprocal Rank Fusion (RRF, k=60), rồi gộp kết quả về section cha (mục 2-4 kế hoạch 2-C).

Cú pháp BM25/dense đã spike thật trên DB dev (mục 2, kế hoạch) — không đoán từ tài liệu ParadeDB.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

BM25_TOP_K = 30
DENSE_TOP_K = 30
RRF_K = 60
SECTION_TOKEN_BUDGET = 3000  # tổng token các section cha đưa vào prompt LLM (mục 4, kế hoạch 2-C/2-D)


@dataclass(frozen=True)
class SectionEvidence:
    section_id: int
    heading: str | None
    content: str
    token_count: int
    chunk_ids: tuple[int, ...]  # các chunk con đã khớp, thuộc section này (dùng để kiểm chunk_id ở validator)
    score: float
    document_title: str
    version_label: str
    # `document_versions.storage_key`: URL Cloudinary thật (production/demo) hoặc đường dẫn tương đối cục bộ
    # (dev/CI, storage_provider=local — không phải URL mở được). FE chỉ hiện thành link khi bắt đầu bằng http.
    document_url: str
    # Dùng để gọi `GET /api/v1/chat/documents/{version_id}` — FE hiện toàn bộ nội dung, cuộn tới đúng section.
    version_id: int


def _format_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(v) for v in vector) + "]"


async def _bm25_search(
    session: AsyncSession, *, lexical_query: str, as_of: date, model_version: str, top_k: int
) -> list[tuple[int, int]]:
    """Trả về [(chunk_id, section_id)] sắp theo điểm BM25 giảm dần."""
    if not lexical_query.strip():
        return []
    rows = await session.execute(
        text(
            """
            SELECT c.id AS chunk_id, c.section_id
            FROM document_chunks c
            JOIN document_versions v ON v.id = c.version_id
            JOIN documents d ON d.id = v.document_id
            WHERE c.lexical_text @@@ :lexical_query
              AND v.status = 'ACTIVE'
              AND d.status = 'ACTIVE'
              AND v.effective_from <= :as_of
              AND (v.effective_to IS NULL OR v.effective_to >= :as_of)
              AND c.embedding_model_version = :model_version
            ORDER BY paradedb.score(c.id) DESC
            LIMIT :top_k
            """
        ),
        {"lexical_query": lexical_query, "as_of": as_of, "model_version": model_version, "top_k": top_k},
    )
    return [(row.chunk_id, row.section_id) for row in rows]


async def _dense_search(
    session: AsyncSession, *, query_vector: list[float], as_of: date, model_version: str, top_k: int
) -> list[tuple[int, int]]:
    """Trả về [(chunk_id, section_id)] sắp theo khoảng cách cosine tăng dần (gần nhất trước)."""
    rows = await session.execute(
        text(
            """
            SELECT c.id AS chunk_id, c.section_id
            FROM document_chunks c
            JOIN document_versions v ON v.id = c.version_id
            JOIN documents d ON d.id = v.document_id
            WHERE v.status = 'ACTIVE'
              AND d.status = 'ACTIVE'
              AND v.effective_from <= :as_of
              AND (v.effective_to IS NULL OR v.effective_to >= :as_of)
              AND c.embedding_model_version = :model_version
            ORDER BY c.embedding <=> CAST(:query_vector AS vector)
            LIMIT :top_k
            """
        ),
        {
            "query_vector": _format_vector_literal(query_vector),
            "as_of": as_of,
            "model_version": model_version,
            "top_k": top_k,
        },
    )
    return [(row.chunk_id, row.section_id) for row in rows]


def reciprocal_rank_fusion(*ranked_lists: list[int], k: int = RRF_K) -> dict[int, float]:
    """Hợp nhất nhiều danh sách đã xếp hạng (id, giảm dần theo độ liên quan) thành một điểm số duy nhất."""
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
    return scores


async def search_to_sections(
    session: AsyncSession,
    *,
    lexical_query: str,
    query_vector: list[float],
    as_of: date,
    model_version: str,
) -> list[SectionEvidence]:
    """Tìm kiếm hybrid cho MỘT câu hỏi, trả về section cha đã gộp, sắp theo độ liên quan, cắt theo ngân sách
    token (mục 3-4, kế hoạch 2-C/2-D). Không gọi LLM ở đây.
    """
    bm25_rows = await _bm25_search(
        session, lexical_query=lexical_query, as_of=as_of, model_version=model_version, top_k=BM25_TOP_K
    )
    dense_rows = await _dense_search(
        session, query_vector=query_vector, as_of=as_of, model_version=model_version, top_k=DENSE_TOP_K
    )
    section_by_chunk = dict(bm25_rows) | dict(dense_rows)
    fused = reciprocal_rank_fusion([c for c, _ in bm25_rows], [c for c, _ in dense_rows])
    if not fused:
        return []

    # Gộp điểm chunk về section cha (lấy điểm cao nhất trong các chunk con cùng section).
    section_scores: dict[int, float] = {}
    section_chunk_ids: dict[int, list[int]] = {}
    for chunk_id, score in fused.items():
        section_id = section_by_chunk[chunk_id]
        section_scores[section_id] = max(section_scores.get(section_id, 0.0), score)
        section_chunk_ids.setdefault(section_id, []).append(chunk_id)

    ordered_section_ids = sorted(section_scores, key=lambda sid: section_scores[sid], reverse=True)
    if not ordered_section_ids:
        return []

    rows = (
        await session.execute(
            text(
                """
                SELECT s.id, s.heading, s.content, s.token_count, d.title AS document_title, v.version_label,
                       v.storage_key AS document_url, v.id AS version_id
                FROM document_sections s
                JOIN document_versions v ON v.id = s.version_id
                JOIN documents d ON d.id = v.document_id
                WHERE s.id = ANY(:ids)
                  AND d.status = 'ACTIVE'
                """
            ).bindparams(ids=ordered_section_ids)
        )
    ).all()
    section_row_by_id = {row.id: row for row in rows}

    evidence: list[SectionEvidence] = []
    total_tokens = 0
    for section_id in ordered_section_ids:
        row = section_row_by_id.get(section_id)
        if row is None:
            continue  # section đã bị xóa/không còn hiệu lực giữa lúc tìm và lúc đọc — bỏ qua, không lỗi
        if total_tokens + row.token_count > SECTION_TOKEN_BUDGET and evidence:
            break  # đã có ít nhất 1 section, dừng khi vượt ngân sách; không bao giờ trả 0 evidence nếu có trúng
        evidence.append(
            SectionEvidence(
                section_id=row.id,
                heading=row.heading,
                content=row.content,
                token_count=row.token_count,
                chunk_ids=tuple(section_chunk_ids[section_id]),
                score=section_scores[section_id],
                document_title=row.document_title,
                version_label=row.version_label,
                document_url=row.document_url,
                version_id=row.version_id,
            )
        )
        total_tokens += row.token_count
    return evidence
