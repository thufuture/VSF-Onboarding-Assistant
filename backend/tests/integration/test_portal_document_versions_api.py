"""Vòng đời phiên bản tài liệu trên PostgreSQL thật: nháp, kích hoạt chạy nền, đóng bản cũ, đặt lại bản cũ, sao chép,
sửa nháp (khóa lạc quan), kích hoạt lỗi không để lại dữ liệu nửa vời (plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md
mục 14, 16; sửa lỗi 1 và 2 ở mục 10.2).
"""

from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from portal_docs_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MD_CONTENT,
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
    upload_form,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.model.document import Document
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.job import Job
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.embedding.modal_adapter import EmbeddingServiceError
from src.services.ingest.ingest_service import today_in
from src.services.ingest.lexical import to_lexical_text
from src.services.portal.job_service import (
    JobContext,
    claim_next_job,
    requeue_stale_jobs,
)
from src.services.retrieval.hybrid_search import search_to_sections

pytestmark = pytest.mark.integration

MD_V2 = "# Tài liệu thử\n\n" + "Nội dung phiên bản hai đã được cập nhật khác hẳn phiên bản đầu tiên. " * 20


async def upload(
    client: httpx.AsyncClient,
    category: str,
    source_key: str,
    *,
    label: str = "1.0",
    content: str = MD_CONTENT,
    activate: bool = False,
    document_id: int | None = None,
    effective_from: str | None = "2024-01-01",
) -> httpx.Response:
    form = {**upload_form(category, source_key), "version_label": label}
    if effective_from is None:
        form.pop("effective_from")
    else:
        form["effective_from"] = effective_from
    if activate:
        form["activate"] = "true"
    if document_id is not None:
        form["document_id"] = str(document_id)
    return await client.post(
        "/api/v1/portal/documents",
        data=form,
        files={"file": ("tai-lieu.md", content.encode("utf-8"), "text/markdown")},
    )


async def versions_of(client: httpx.AsyncClient, document_id: int) -> dict[str, dict[str, Any]]:
    response = await client.get(f"/api/v1/portal/documents/{document_id}/versions")
    assert response.status_code == 200, response.text
    return {row["version_label"]: row for row in response.json()}


async def activate_and_run(
    client: httpx.AsyncClient, ctx: JobContext, document_id: int, version_id: int, **body: object
) -> dict[str, Any]:
    response = await client.post(f"/api/v1/portal/documents/{document_id}/versions/{version_id}/activate", json=body)
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    await run_jobs(ctx)
    job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
    assert isinstance(job, dict)
    return job


async def test_activating_new_version_closes_old_one(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Lỗi 1 (mục 10.2): tải phiên bản mới của cùng tài liệu trước đây thất bại vì bản cũ không bao giờ được đóng."""
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    today = today_in()

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        doc_id = first["document_id"]

        second = (
            await upload(
                client,
                category,
                source_key,
                label="v2",
                content=MD_V2,
                document_id=doc_id,
                effective_from=today.isoformat(),
            )
        ).json()
        job = await activate_and_run(client, job_ctx, doc_id, second["document_version_id"])
        assert job["status"] == "SUCCEEDED", job
        assert job["result"]["closed_version_ids"] == [first["document_version_id"]]

        rows = await versions_of(client, doc_id)
        assert rows["v2"]["state"] == "CURRENT"
        assert rows["v1"]["state"] == "SUPERSEDED"
        assert rows["v1"]["status"] == "ARCHIVED"
        assert rows["v1"]["effective_to"] == (today - timedelta(days=1)).isoformat()
        assert rows["v2"]["effective_from"] == today.isoformat()
        assert rows["v2"]["effective_to"] is None

    async with session_factory() as session:
        active = await session.scalar(
            select(func.count())
            .select_from(DocumentVersion)
            .where(DocumentVersion.document_id == doc_id, DocumentVersion.status == "ACTIVE")
        )
        assert active == 1


async def test_future_dated_version_keeps_old_one_serving_until_then(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    today = today_in()
    tomorrow = today + timedelta(days=3)

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        doc_id = first["document_id"]
        second = (
            await upload(
                client,
                category,
                source_key,
                label="v2",
                content=MD_V2,
                document_id=doc_id,
                effective_from=tomorrow.isoformat(),
            )
        ).json()
        job = await activate_and_run(client, job_ctx, doc_id, second["document_version_id"])
        assert job["status"] == "SUCCEEDED", job

        rows = await versions_of(client, doc_id)
        assert rows["v2"]["state"] == "SCHEDULED"
        assert rows["v1"]["state"] == "CURRENT"  # vẫn áp dụng tới hết ngày trước ngày hiệu lực mới
        assert rows["v1"]["effective_to"] == (tomorrow - timedelta(days=1)).isoformat()


async def test_set_old_version_as_current_reuses_embeddings(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """ "Đặt làm bản áp dụng" cho bản cũ: quay về bản trước, không tốn embedding, section giữ nguyên mã."""
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        doc_id, v1_id = first["document_id"], first["document_version_id"]
        second = (await upload(client, category, source_key, label="v2", content=MD_V2, document_id=doc_id)).json()
        await activate_and_run(client, job_ctx, doc_id, second["document_version_id"])

        async with session_factory() as session:
            before = list(
                (await session.scalars(select(DocumentSection.id).where(DocumentSection.version_id == v1_id))).all()
            )

        job = await activate_and_run(client, job_ctx, doc_id, v1_id)
        assert job["status"] == "SUCCEEDED", job
        assert job["result"]["reused_embeddings"] is True
        rows = await versions_of(client, doc_id)
        assert rows["v1"]["state"] == "CURRENT"
        assert rows["v2"]["state"] == "SUPERSEDED"

        async with session_factory() as session:
            after = list(
                (await session.scalars(select(DocumentSection.id).where(DocumentSection.version_id == v1_id))).all()
            )
        assert before == after

        # Đặt lại đúng bản đang áp dụng thì từ chối, không tạo việc thừa.
        again = await client.post(f"/api/v1/portal/documents/{doc_id}/versions/{v1_id}/activate", json={})
        assert again.status_code == 409
        assert again.json()["code"] == "VERSION_ALREADY_CURRENT"


async def test_copy_edit_and_delete_draft(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        doc_id, v1_id = first["document_id"], first["document_version_id"]

        copy = await client.post(f"/api/v1/portal/documents/{doc_id}/versions/{v1_id}/copy", json={})
        assert copy.status_code == 201, copy.text
        draft = copy.json()
        assert draft["state"] == "DRAFT"
        assert draft["parent_version_id"] == v1_id
        assert draft["version_label"] == "v1 (sao chép)"

        # Sửa nội dung nháp.
        new_text = MD_V2
        edited = await client.patch(
            f"/api/v1/portal/documents/{doc_id}/versions/{draft['id']}",
            json={"expected_updated_at": draft["updated_at"], "markdown": new_text, "label": "v1.1"},
        )
        assert edited.status_code == 200, edited.text
        assert edited.json()["version_label"] == "v1.1"
        assert edited.json()["source"] == "EDITED"

        # Khóa lạc quan: dùng `updated_at` cũ (người khác đã lưu trước) thì bị từ chối.
        stale = await client.patch(
            f"/api/v1/portal/documents/{doc_id}/versions/{draft['id']}",
            json={"expected_updated_at": draft["updated_at"], "label": "v1.2"},
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "VERSION_CONFLICT"

        # Nội dung quá ngắn bị từ chối.
        short = await client.patch(
            f"/api/v1/portal/documents/{doc_id}/versions/{draft['id']}",
            json={"expected_updated_at": edited.json()["updated_at"], "markdown": "ngắn"},
        )
        assert short.status_code == 422
        assert short.json()["code"] == "VERSION_CONTENT_TOO_SHORT"

        # Bản đang áp dụng không sửa tại chỗ và không xóa được.
        locked = await client.patch(
            f"/api/v1/portal/documents/{doc_id}/versions/{v1_id}",
            json={"expected_updated_at": first_updated(await versions_of(client, doc_id), "v1"), "label": "x"},
        )
        assert locked.status_code == 409
        assert locked.json()["code"] == "VERSION_NOT_EDITABLE"
        assert (await client.delete(f"/api/v1/portal/documents/{doc_id}/versions/{v1_id}")).status_code == 409

        # Xóa nháp được.
        assert (await client.delete(f"/api/v1/portal/documents/{doc_id}/versions/{draft['id']}")).status_code == 204
        assert "v1.1" not in await versions_of(client, doc_id)


def first_updated(rows: dict[str, dict[str, Any]], label: str) -> object:
    return rows[label]["updated_at"]


async def test_failed_activation_leaves_database_clean_and_restores_draft(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    class BrokenEmbedding(FakeEmbeddingAdapter):
        async def embed(self, texts: list[str]) -> list[list[float]]:
            raise EmbeddingServiceError("dịch vụ embedding không phản hồi")

    broken = JobContext(
        session_factory=job_ctx.session_factory,
        embedding=BrokenEmbedding(),
        storage=job_ctx.storage,
        make_llm=job_ctx.make_llm,
    )

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        doc_id = first["document_id"]
        second = (await upload(client, category, source_key, label="v2", content=MD_V2, document_id=doc_id)).json()

        activate = await client.post(
            f"/api/v1/portal/documents/{doc_id}/versions/{second['document_version_id']}/activate", json={}
        )
        job_id = activate.json()["id"]
        # Lỗi embedding được thử lại (retryable) rồi hết lượt: chạy tới khi job dừng hẳn.
        for _ in range(5):
            await run_jobs(broken)
            async with session_factory() as session:
                await session.execute(
                    update(Job).where(Job.id == job_id, Job.status == "PENDING").values(run_after=func.now())
                )
                await session.commit()
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
        assert job["status"] == "FAILED", job
        assert "EMBEDDING_FAILED" in job["error"]

        rows = await versions_of(client, doc_id)
        assert rows["v2"]["state"] == "DRAFT"  # trả về nháp, HR sửa/thử lại được
        assert "EMBEDDING_FAILED" in str(rows["v2"]["failure_reason"])
        assert rows["v2"]["section_count"] == 0
        assert rows["v1"]["state"] == "CURRENT"  # bản cũ vẫn chạy

    async with session_factory() as session:
        chunks = await session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.version_id == second["document_version_id"])
        )
        assert chunks == 0


async def test_progress_is_monotonic_and_reported_per_embedding_batch(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    seen: list[int] = []

    class RecordingEmbedding(FakeEmbeddingAdapter):
        async def embed(self, texts: list[str]) -> list[list[float]]:
            async with session_factory() as session:
                value = await session.scalar(select(Job.progress_percent).order_by(Job.id.desc()).limit(1))
                seen.append(int(value or 0))
            return await super().embed(texts)

    ctx = JobContext(
        session_factory=job_ctx.session_factory,
        embedding=RecordingEmbedding(),
        storage=job_ctx.storage,
        make_llm=job_ctx.make_llm,
    )
    # Nhiều đoạn văn dài để vượt một lô embedding (32 chuỗi).
    big = "# Tài liệu lớn\n\n" + "\n\n".join(
        f"## Mục {i}\n\n" + (f"Nội dung mục số {i} rất cụ thể. " * 40) for i in range(80)
    )

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", content=big, activate=True)).json()
        job_id = first["job_id"]
        await run_jobs(ctx)
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()

    assert job["status"] == "SUCCEEDED", job
    assert job["result"]["chunk_count"] > 32
    batches = [value for value in seen if value >= 20]
    assert len(batches) >= 2, seen
    assert batches == sorted(batches), seen  # tiến độ không bao giờ lùi
    assert batches[-1] < 80 and job["progress_percent"] == 100


async def test_archived_document_and_old_versions_are_not_found_by_viga(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Lỗi 2 (mục 10.2): tài liệu ngừng sử dụng vẫn bị Viga tìm thấy; bản đã thay thế cũng không được tìm."""
    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    embedding = FakeEmbeddingAdapter()
    question = "Nội dung dùng để test upload qua API Portal."
    vector = (await embedding.embed([question]))[0]
    today = today_in()

    async def search() -> list[str]:
        async with session_factory() as session:
            found = await search_to_sections(
                session,
                lexical_query=to_lexical_text(question),
                query_vector=vector,
                as_of=today,
                model_version=embedding.model_version,
            )
        return [item.version_label for item in found]

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        doc_id = first["document_id"]
        assert "v1" in await search()

        # Bản mới thay thế: Viga không còn trả bản v1.
        second = (await upload(client, category, source_key, label="v2", content=MD_V2, document_id=doc_id)).json()
        await activate_and_run(client, job_ctx, doc_id, second["document_version_id"])
        assert "v1" not in await search()

        # Ngừng sử dụng tài liệu: Viga không tìm thấy nữa.
        resp = await client.patch(f"/api/v1/portal/documents/{doc_id}/status", json={"status": "ARCHIVED"})
        assert resp.status_code == 200, resp.text
        assert await search() == []

    async with session_factory() as session:
        document = await session.get(Document, doc_id)
        assert document is not None and document.status == "ARCHIVED"


async def test_employee_cannot_read_draft_but_can_read_current_version(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    employee = await make_member("USER", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", activate=True)).json()
        await run_jobs(job_ctx)
        draft = (
            await upload(client, category, source_key, label="v2", content=MD_V2, document_id=first["document_id"])
        ).json()

    async with client_for(app) as client:
        await login(client, employee)
        current = await client.get(f"/api/v1/chat/documents/{first['document_version_id']}")
        assert current.status_code == 200
        hidden = await client.get(f"/api/v1/chat/documents/{draft['document_version_id']}")
        assert hidden.status_code == 404

    async with client_for(app) as client:
        await login(client, hr)
        # HR vẫn xem được bản nháp để duyệt trước khi kích hoạt.
        assert (await client.get(f"/api/v1/chat/documents/{draft['document_version_id']}")).status_code == 200


async def test_jobs_are_visible_only_to_creator_or_admin(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    owner = await make_member("HR", team.id)
    other = await make_member("HR", team.id)
    admin = await make_member("ADMIN", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, owner)
        job_id = (await upload(client, category, source_key, label="v1", activate=True)).json()["job_id"]
        assert (await client.get(f"/api/v1/portal/jobs/{job_id}")).status_code == 200
        mine = (await client.get("/api/v1/portal/jobs?active=true")).json()
        assert [row["id"] for row in mine] == [job_id]

    async with client_for(app) as client:
        await login(client, other)
        denied = await client.get(f"/api/v1/portal/jobs/{job_id}")
        assert denied.status_code == 404
        assert (await client.get("/api/v1/portal/jobs?active=true")).json() == []

    async with client_for(app) as client:
        await login(client, admin)
        assert (await client.get(f"/api/v1/portal/jobs/{job_id}")).status_code == 200


async def test_stale_running_job_is_requeued_then_failed_and_version_restored(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from src.services.portal.job_handlers import HANDLERS

    hr = await make_member("HR", team.id)
    source_key = f"ver-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        created = (await upload(client, category, source_key, label="v1", activate=True)).json()
        job_id = created["job_id"]

        # Worker lấy job rồi "chết" giữa chừng: job RUNNING nhưng không còn báo nhịp sống.
        claimed = await claim_next_job(session_factory, "worker-chet")
        assert claimed is not None and claimed.id == job_id
        old = func.now() - timedelta(hours=1)
        async with session_factory() as session:
            await session.execute(update(Job).where(Job.id == job_id).values(locked_at=old))
            await session.commit()

        assert await requeue_stale_jobs(job_ctx, HANDLERS, 300) == 1
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
        assert job["status"] == "PENDING"  # còn lượt (attempts 1/2) nên về hàng đợi

        async with session_factory() as session:
            await session.execute(update(Job).where(Job.id == job_id).values(run_after=func.now()))
            await session.commit()
        claimed = await claim_next_job(session_factory, "worker-chet-2")
        assert claimed is not None and claimed.attempts == 2
        async with session_factory() as session:
            await session.execute(update(Job).where(Job.id == job_id).values(locked_at=old))
            await session.commit()

        assert await requeue_stale_jobs(job_ctx, HANDLERS, 300) == 1
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
        assert job["status"] == "FAILED"  # hết lượt
        assert "JOB_INTERRUPTED" in job["error"]

        rows = await versions_of(client, created["document_id"])
        assert rows["v1"]["state"] == "DRAFT"  # trả về nháp, không kẹt ở "Đang xử lý"
