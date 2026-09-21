"""0001_core trên PostgreSQL/ParadeDB thật: bảng, extension và các bất biến ở tầng DB (database-design mục 3.1)."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from src.model.base import EMBEDDING_DIMENSION

pytestmark = pytest.mark.integration

CORE_TABLES = {
    "users",
    "teams",
    "team_members",
    "document_categories",
    "documents",
    "document_versions",
    "document_sections",
    "document_chunks",
    "jobs",
    "audit_logs",
}


async def _scalar(conn: AsyncConnection, sql: str, **params: object) -> Any:
    return (await conn.execute(text(sql), params)).scalar_one()


async def _new_id(conn: AsyncConnection, sql: str, **params: object) -> int:
    return int(await _scalar(conn, sql, **params))


async def _new_user(conn: AsyncConnection, email: str = "hr@example.test") -> int:
    return await _new_id(
        conn,
        "INSERT INTO users (email, display_name, password_hash, role) VALUES (:email, 'HR', 'x', 'HR') RETURNING id",
        email=email,
    )


async def _new_document(conn: AsyncConnection, owner_id: int, **overrides: object) -> int:
    category_id = await _scalar(
        conn, "INSERT INTO document_categories (slug, name) VALUES ('nghi-phep', 'Nghỉ phép') RETURNING id"
    )
    params = {"category_id": category_id, "owner_id": owner_id, "confidentiality": "INTERNAL", **overrides}
    return await _new_id(
        conn,
        "INSERT INTO documents (title, category_id, owner_id, confidentiality) "
        "VALUES ('Chính sách nghỉ phép', :category_id, :owner_id, :confidentiality) RETURNING id",
        **params,
    )


async def _add_version(
    conn: AsyncConnection,
    document_id: int,
    uploaded_by: int,
    *,
    label: str,
    revision: int,
    status: str = "ACTIVE",
    effective_from: date | None = None,
    effective_to: date | None = None,
) -> int:
    return await _new_id(
        conn,
        """INSERT INTO document_versions
                 (document_id, version_label, revision_no, status, original_filename, mime_type, size_bytes,
                  storage_key, file_checksum, content_checksum, parser, markdown, effective_from, effective_to,
                  embedding_model_version, uploaded_by)
               VALUES (:document_id, :label, :revision, :status, 'a.docx', 'application/octet-stream', 1,
                       'k', 'f', 'c', 'markitdown', '# a', :effective_from, :effective_to, 'test', :uploaded_by)
               RETURNING id""",
        document_id=document_id,
        label=label,
        revision=revision,
        status=status,
        effective_from=effective_from,
        effective_to=effective_to,
        uploaded_by=uploaded_by,
    )


async def test_core_tables_and_extensions_exist(conn: AsyncConnection) -> None:
    tables = {
        row[0]
        for row in await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"))
    }
    assert CORE_TABLES <= tables
    assert "sessions" not in tables  # phiên là cookie HMAC + users.session_invalid_before
    extensions = {row[0] for row in await conn.execute(text("SELECT extname FROM pg_extension"))}
    assert {"vector", "pg_search", "btree_gist"} <= extensions


async def test_overlapping_active_versions_are_rejected(conn: AsyncConnection) -> None:
    user_id = await _new_user(conn)
    document_id = await _new_document(conn, user_id)
    await _add_version(
        conn,
        document_id,
        user_id,
        label="1.0",
        revision=1,
        effective_from=date(2023, 1, 1),
        effective_to=date(2024, 12, 31),
    )

    async def add(
        label: str,
        revision: int,
        status: str = "ACTIVE",
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> None:
        async with conn.begin_nested():  # savepoint: lỗi không làm hỏng transaction của test
            await _add_version(
                conn,
                document_id,
                user_id,
                label=label,
                revision=revision,
                status=status,
                effective_from=effective_from,
                effective_to=effective_to,
            )

    with pytest.raises(IntegrityError):
        await add("2.0", 2, effective_from=date(2024, 6, 1), effective_to=date(2025, 6, 1))
    # Ngày rời nhau: được (v2023 hết hiệu lực trước khi v2025 bắt đầu).
    await add("3.0", 3, effective_from=date(2025, 1, 1))
    # Chồng ngày nhưng không ACTIVE: được.
    await add("2.5", 4, status="ARCHIVED", effective_from=date(2024, 6, 1), effective_to=date(2025, 6, 1))


async def test_open_ended_active_versions_overlap(conn: AsyncConnection) -> None:
    # Ngày trống nghĩa là không giới hạn, nên hai bản ACTIVE đều không có ngày là chồng nhau.
    user_id = await _new_user(conn)
    document_id = await _new_document(conn, user_id)
    await _add_version(conn, document_id, user_id, label="1.0", revision=1)
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await _add_version(conn, document_id, user_id, label="2.0", revision=2)


async def test_version_label_and_revision_are_unique_per_document(conn: AsyncConnection) -> None:
    user_id = await _new_user(conn)
    document_id = await _new_document(conn, user_id)
    await _add_version(conn, document_id, user_id, label="1.0", revision=1, status="ARCHIVED")
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await _add_version(conn, document_id, user_id, label="1.0", revision=2, status="ARCHIVED")  # INV5
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await _add_version(conn, document_id, user_id, label="1.1", revision=1, status="ARCHIVED")


async def test_effective_dates_must_be_ordered(conn: AsyncConnection) -> None:  # INV12
    user_id = await _new_user(conn)
    document_id = await _new_document(conn, user_id)
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await _add_version(
                conn,
                document_id,
                user_id,
                label="1.0",
                revision=1,
                effective_from=date(2025, 1, 1),
                effective_to=date(2024, 1, 1),
            )


async def test_only_low_sensitivity_documents_are_accepted(conn: AsyncConnection) -> None:  # INV9
    user_id = await _new_user(conn)
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await _new_document(conn, user_id, confidentiality="SECRET")


async def test_email_is_unique_case_insensitively(conn: AsyncConnection) -> None:
    await _new_user(conn, "Someone@Example.test")
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await _new_user(conn, "someone@example.TEST")


async def test_two_active_jobs_cannot_share_an_idempotency_key(conn: AsyncConnection) -> None:  # INV10
    insert = text("INSERT INTO jobs (kind, idempotency_key, status) VALUES ('INGEST_VERSION', 'k1', :status)")
    await conn.execute(insert, {"status": "PENDING"})
    with pytest.raises(IntegrityError):
        async with conn.begin_nested():
            await conn.execute(insert, {"status": "RUNNING"})
    # Job đã xong không chặn job mới cùng khóa.
    await conn.execute(insert, {"status": "SUCCEEDED"})
    await conn.execute(insert, {"status": "SUCCEEDED"})


async def test_chunks_store_1024_dimensional_vectors_and_rank_by_cosine(conn: AsyncConnection) -> None:
    user_id = await _new_user(conn)
    document_id = await _new_document(conn, user_id)
    version_id = await _add_version(conn, document_id, user_id, label="1.0", revision=1)
    section_id = await _scalar(
        conn,
        "INSERT INTO document_sections (version_id, section_index, content, token_count) "
        "VALUES (:v, 0, 'nội dung', 2) RETURNING id",
        v=version_id,
    )

    def vector(first: float) -> str:
        values = [first, 1.0] + [0.0] * (EMBEDDING_DIMENSION - 2)
        return "[" + ",".join(str(v) for v in values) + "]"

    for index, first in enumerate((1.0, -1.0)):
        await conn.execute(
            text(
                """INSERT INTO document_chunks
                     (section_id, version_id, chunk_index, content, embedding_text, lexical_text, content_hash,
                      token_count, embedding_model_version, embedding)
                   VALUES (:s, :v, :i, 'c', 'c', 'c', 'h', 1, 'test', CAST(:e AS vector))"""
            ),
            {"s": section_id, "v": version_id, "i": index, "e": vector(first)},
        )
    nearest = await _scalar(
        conn,
        "SELECT chunk_index FROM document_chunks ORDER BY embedding <=> CAST(:q AS vector) LIMIT 1",
        q=vector(1.0),
    )
    assert nearest == 0

    with pytest.raises(Exception, match="dimensions"):
        async with conn.begin_nested():
            await conn.execute(
                text(
                    """INSERT INTO document_chunks
                         (section_id, version_id, chunk_index, content, embedding_text, lexical_text, content_hash,
                          token_count, embedding_model_version, embedding)
                       VALUES (:s, :v, 9, 'c', 'c', 'c', 'h', 1, 'test', CAST('[1,2,3]' AS vector))"""
                ),
                {"s": section_id, "v": version_id},
            )


async def test_bm25_and_hnsw_indexes_exist(conn: AsyncConnection) -> None:
    rows = await conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks'"))
    definitions = {name: definition for name, definition in rows}
    assert "USING hnsw" in definitions["ix_document_chunks_embedding"]
    assert "vector_cosine_ops" in definitions["ix_document_chunks_embedding"]
    assert "USING bm25" in definitions["ix_document_chunks_bm25"]
