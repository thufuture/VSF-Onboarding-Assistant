"""HR tải tài liệu qua `/api/v1/portal/documents` trên PostgreSQL thật (plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md
mục 16.3): tải file chỉ tạo **bản nháp** (nhanh, chưa embedding); "tải và kích hoạt luôn" trả `job_id` (HTTP 202).
"""

from types import SimpleNamespace
from uuid import uuid4

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.model.document_chunk import DocumentChunk
from src.model.document_version import DocumentVersion
from src.services.portal.job_service import JobContext

pytestmark = pytest.mark.integration


async def test_hr_uploads_document_as_draft(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"upload-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/documents",
            data=upload_form(category, source_key),
            files={"file": ("test.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["created_document"] is True
    assert body["reused"] is False
    assert body["job_id"] is None
    async with session_factory() as session:
        version = await session.get(DocumentVersion, body["document_version_id"])
        assert version is not None
        assert version.status == "DRAFT"
        assert version.markdown.startswith("# Tài liệu thử")
        # Bản nháp chưa cắt chunk và chưa embedding: Viga không thể thấy nó.
        chunks = (await session.scalars(select(DocumentChunk).where(DocumentChunk.version_id == version.id))).all()
        assert chunks == []


async def test_user_role_cannot_upload(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        response = await client.post(
            "/api/v1/portal/documents",
            data=upload_form(category, f"upload-{uuid4().hex[:10]}"),
            files={"file": ("test.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"


async def test_reupload_same_content_is_idempotent(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"upload-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    form = upload_form(category, source_key)

    async with client_for(app) as client:
        await login(client, hr)
        first = await client.post(
            "/api/v1/portal/documents",
            data=form,
            files={"file": ("test.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
        )
        second = await client.post(
            "/api/v1/portal/documents",
            data=form,
            files={"file": ("test.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
        )

    assert first.json()["reused"] is False
    assert second.json()["reused"] is True
    assert first.json()["document_version_id"] == second.json()["document_version_id"]


async def test_same_label_with_different_content_is_rejected(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"upload-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    form = upload_form(category, source_key)

    async with client_for(app) as client:
        await login(client, hr)
        await client.post(
            "/api/v1/portal/documents",
            data=form,
            files={"file": ("test.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
        )
        other = await client.post(
            "/api/v1/portal/documents",
            data=form,
            files={"file": ("test.md", (MD_CONTENT + "\n\nĐã sửa thêm một đoạn.").encode("utf-8"), "text/markdown")},
        )

    assert other.status_code == 409
    assert other.json()["code"] == "VERSION_LABEL_EXISTS"


async def test_upload_and_activate_runs_in_background_with_progress(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"upload-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/documents",
            data={**upload_form(category, source_key), "activate": "true"},
            files={"file": ("test.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
        )
        assert response.status_code == 202, response.text
        job_id = response.json()["job_id"]
        assert job_id is not None

        queued = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
        assert queued["status"] == "PENDING"
        assert queued["progress_percent"] == 0

        assert await run_jobs(job_ctx) >= 1

        done = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
        assert done["status"] == "SUCCEEDED", done
        assert done["progress_percent"] == 100
        assert done["result"]["chunk_count"] >= 1
        assert done["result"]["section_count"] >= 1
