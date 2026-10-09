"""Kích hoạt phiên bản dùng lại vector của đoạn không đổi (EMBEDDING_CACHE_ENABLED), trên PostgreSQL thật.

Điều cần chứng minh: (1) sửa một chỗ thì chỉ tính lại đúng đoạn đó; (2) kết quả lưu giống hệt cách tính toàn bộ;
(3) khác model thì không dùng lại; (4) cờ tắt thì hành vi cũ (tính hết).
"""

from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from portal_docs_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    app,
    category,
    cleanup_documents,
    client_for,
    job_ctx,
    login,
    make_member,
    run_jobs,
    session_factory,
    team,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from test_portal_document_versions_api import activate_and_run, upload

from src.model.document_chunk import DocumentChunk
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.ingest_service import today_in
from src.services.portal.job_service import JobContext

pytestmark = pytest.mark.integration


class CountingEmbedding(FakeEmbeddingAdapter):
    def __init__(self, model_version: str | None = None) -> None:
        self.calls: list[str] = []
        if model_version is not None:
            self.model_version = model_version

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.extend(texts)
        return await super().embed(texts)


def build_doc(section_bodies: list[str]) -> str:
    return "# Quy định thử\n\n" + "\n\n".join(
        f"## Điều {i}\n\n{body}" for i, body in enumerate(section_bodies, start=1)
    )


BODIES = [
    f"Nội dung điều số {i} có nhiều chữ khác nhau để thành một đoạn riêng. " * 12 + f"Mã {i}." for i in range(1, 7)
]


async def chunk_rows(session_factory: async_sessionmaker[AsyncSession], version_id: int) -> list[DocumentChunk]:
    async with session_factory() as session:
        return list(
            (
                await session.scalars(
                    select(DocumentChunk)
                    .where(DocumentChunk.version_id == version_id)
                    .order_by(DocumentChunk.chunk_index)
                )
            ).all()
        )


async def activate_two_versions(
    app: FastAPI,
    category: str,
    hr: SimpleNamespace,
    source_key: str,
    ctx_first: JobContext,
    ctx_second: JobContext,
    second_markdown: str,
) -> tuple[int, int, dict[str, object]]:
    async with client_for(app) as client:
        await login(client, hr)
        first = (
            await upload(client, category, source_key, label="v1", content=build_doc(BODIES), activate=True)
        ).json()
        await run_jobs(ctx_first)
        second = (
            await upload(
                client,
                category,
                source_key,
                label="v2",
                content=second_markdown,
                document_id=first["document_id"],
                effective_from=today_in().isoformat(),
            )
        ).json()
        job = await activate_and_run(client, ctx_second, first["document_id"], second["document_version_id"])
    return first["document_version_id"], second["document_version_id"], job


async def test_editing_one_section_only_reembeds_that_chunk(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"reuse-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    first_embedding, second_embedding = CountingEmbedding(), CountingEmbedding()
    ctx_first = replace(job_ctx, embedding=first_embedding, embedding_cache_enabled=True)
    ctx_second = replace(job_ctx, embedding=second_embedding, embedding_cache_enabled=True)
    edited = list(BODIES)
    edited[2] = edited[2].replace("Mã 3.", "Mã 3 đã được sửa.")

    v1, v2, job = await activate_two_versions(app, category, hr, source_key, ctx_first, ctx_second, build_doc(edited))

    assert job["status"] == "SUCCEEDED", job
    old_rows, new_rows = await chunk_rows(session_factory, v1), await chunk_rows(session_factory, v2)
    assert len(old_rows) == len(new_rows) > 1
    assert len(first_embedding.calls) == len(old_rows)  # bản đầu chưa có gì để dùng lại
    changed = [row for row in new_rows if "đã được sửa" in row.content]
    assert len(changed) == 1
    assert len(second_embedding.calls) == 1 and second_embedding.calls[0] == changed[0].embedding_text
    assert job["result"]["reused_chunks"] == len(new_rows) - 1
    # Vector lưu giống hệt cách tính từ đầu (đoạn dùng lại và đoạn tính mới).
    expected = await FakeEmbeddingAdapter().embed([row.embedding_text for row in new_rows])
    for row, vector in zip(new_rows, expected, strict=True):
        assert row.embedding is not None
        assert [round(float(x), 5) for x in row.embedding] == [round(x, 5) for x in vector]


async def test_identical_new_version_embeds_nothing(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"reuse-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    second_embedding = CountingEmbedding()
    _, _, job = await activate_two_versions(
        app,
        category,
        hr,
        source_key,
        replace(job_ctx, embedding=CountingEmbedding(), embedding_cache_enabled=True),
        replace(job_ctx, embedding=second_embedding, embedding_cache_enabled=True),
        build_doc(BODIES),
    )
    assert job["status"] == "SUCCEEDED", job
    assert second_embedding.calls == []
    assert job["result"]["chunk_count"] == job["result"]["reused_chunks"] > 0


async def test_different_model_version_is_never_reused(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"reuse-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    second_embedding = CountingEmbedding(model_version="fake-embedding-other")
    _, _, job = await activate_two_versions(
        app,
        category,
        hr,
        source_key,
        replace(job_ctx, embedding=CountingEmbedding(), embedding_cache_enabled=True),
        replace(job_ctx, embedding=second_embedding, embedding_cache_enabled=True),
        build_doc(BODIES),
    )
    assert job["status"] == "SUCCEEDED", job
    assert len(second_embedding.calls) == job["result"]["chunk_count"]
    assert job["result"]["reused_chunks"] == 0


async def test_flag_off_embeds_everything_like_before(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"reuse-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    second_embedding = CountingEmbedding()
    _, _, job = await activate_two_versions(
        app,
        category,
        hr,
        source_key,
        replace(job_ctx, embedding=CountingEmbedding()),
        replace(job_ctx, embedding=second_embedding),
        build_doc(BODIES),
    )
    assert job["status"] == "SUCCEEDED", job
    assert len(second_embedding.calls) == job["result"]["chunk_count"]
    assert job["result"]["reused_chunks"] == 0
