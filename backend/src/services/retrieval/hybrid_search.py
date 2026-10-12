"""Tìm kiếm hybrid trên `document_chunks`: BM25 (`pg_search`, toán tử `@@@`) + dense (`pgvector`, `<=>`),
hợp nhất bằng Reciprocal Rank Fusion (RRF, k=60), rồi gộp kết quả về section cha (mục 2-4 kế hoạch 2-C).

Cú pháp BM25/dense đã spike thật trên DB dev (mục 2, kế hoạch) — không đoán từ tài liệu ParadeDB.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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


# Ký tự có nghĩa trong cú pháp truy vấn của ParadeDB (`[a TO b]`, nhóm, cụm từ, trường, toán tử...). Người dùng gõ
# bình thường (ví dụ trích nhãn `[TRONG TÀI LIỆU NGÀY 1]`) có thể làm cả truy vấn bị từ chối.
_QUERY_SYNTAX_CHARS = re.compile("[" + re.escape("[]{}()\"~^*?:\\+!/&|<>=,;'`-") + "]")
_PARSE_ERROR_MARKER = "could not parse query string"


def sanitize_lexical_query(query: str) -> str:
    """Thay ký tự cú pháp truy vấn bằng khoảng trắng; giữ nguyên chữ và số."""
    return " ".join(_QUERY_SYNTAX_CHARS.sub(" ", query).split())


async def _bm25_search(
    session: AsyncSession, *, lexical_query: str, as_of: date, model_version: str, top_k: int
) -> list[tuple[int, int]]:
    """Trả về [(chunk_id, section_id)] sắp theo điểm BM25 giảm dần.

    Truy vấn gốc được thử trước (không đổi hành vi với câu đang chạy tốt). Nếu ParadeDB từ chối cú pháp thì thử lại
    với bản đã bỏ ký tự cú pháp, trong SAVEPOINT để không làm hỏng giao dịch của người gọi.
    """
    if not lexical_query.strip():
        return []
    try:
        async with session.begin_nested():
            return await _bm25_query(session, lexical_query, as_of, model_version, top_k)
    except DBAPIError as exc:
        if _PARSE_ERROR_MARKER not in str(exc):
            raise
        safe_query = sanitize_lexical_query(lexical_query)
        logger.warning(
            "bm25_query_parse_error: thử lại với truy vấn đã bỏ ký tự cú pháp (độ dài %d)", len(lexical_query)
        )
        if not safe_query:
            return []
        async with session.begin_nested():
            return await _bm25_query(session, safe_query, as_of, model_version, top_k)


async def _bm25_query(
    session: AsyncSession, lexical_query: str, as_of: date, model_version: str, top_k: int
) -> list[tuple[int, int]]:
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


def reciprocal_rank_fusion(
    *ranked_lists: list[int], k: int = RRF_K, weights: tuple[float, ...] | None = None
) -> dict[int, float]:
    """Hợp nhất nhiều danh sách đã xếp hạng (id, giảm dần theo độ liên quan) thành một điểm số duy nhất.

    `weights` là hệ số của từng danh sách theo đúng thứ tự (mặc định mọi danh sách bằng nhau = 1).
    """
    if weights is not None and len(weights) != len(ranked_lists):
        raise ValueError("số hệ số phải bằng số danh sách")
    scores: dict[int, float] = {}
    for index, ranked in enumerate(ranked_lists):
        weight = 1.0 if weights is None else weights[index]
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + weight / (k + rank)
    return scores


def select_with_bm25_reserve(
    ordered_section_ids: list[int], bm25_section_ids: list[int], max_sections: int, bm25_reserve: int
) -> list[int]:
    """Giữ `max_sections` mục: phần lớn theo thứ tự RRF, riêng `bm25_reserve` chỗ dành cho các mục đứng đầu của BM25.

    Bảo hiểm cho trọng số BM25 thấp: câu cần khớp đúng chuỗi (mã form, email, tên riêng) vẫn có mục BM25 xếp đầu trong ngữ
    cảnh dù vector không xếp cao. Mục BM25 được thêm vào cuối; nếu BM25 không còn mục mới thì chỗ đó trả lại cho RRF.
    """
    if max_sections <= 0 or bm25_reserve <= 0 or len(ordered_section_ids) <= max_sections:
        return ordered_section_ids[:max_sections] if max_sections > 0 else ordered_section_ids
    reserve = min(bm25_reserve, max_sections - 1)  # luôn để lại ít nhất 1 chỗ cho thứ hạng RRF
    kept = ordered_section_ids[: max_sections - reserve]
    candidates = [sid for sid in bm25_section_ids if sid not in kept and sid in set(ordered_section_ids)]
    extras = candidates[:reserve]
    kept = kept + extras
    for sid in ordered_section_ids[max_sections - reserve :]:  # chỗ BM25 không dùng hết thì nhường lại cho RRF
        if len(kept) >= max_sections:
            break
        if sid not in kept:
            kept.append(sid)
    return kept


async def search_to_sections(
    session: AsyncSession,
    *,
    lexical_query: str,
    query_vector: list[float],
    as_of: date,
    model_version: str,
    max_sections: int = 0,
    min_score_ratio: float = 0.0,
    rrf_k: int = RRF_K,
    bm25_weight: float = 1.0,
    vector_weight: float = 1.0,
    bm25_reserve: int = 0,
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
    fused = reciprocal_rank_fusion(
        [c for c, _ in bm25_rows], [c for c, _ in dense_rows], k=rrf_k, weights=(bm25_weight, vector_weight)
    )
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
    # Cắt ngữ cảnh (tối ưu có cờ): theo điểm tương đối so với section đầu, rồi theo số section. Mặc định tắt (0).
    if min_score_ratio > 0:
        floor = section_scores[ordered_section_ids[0]] * min_score_ratio
        ordered_section_ids = [sid for sid in ordered_section_ids if section_scores[sid] >= floor]
    if max_sections > 0:
        bm25_section_ids = list(dict.fromkeys(section_id for _, section_id in bm25_rows))
        ordered_section_ids = select_with_bm25_reserve(
            ordered_section_ids, bm25_section_ids, max_sections, bm25_reserve
        )

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
