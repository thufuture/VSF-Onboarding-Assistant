"""PDF scan: tải lên tạo bản nháp chờ OCR, việc nền OCR rồi mở khóa bản nháp (công cụ OCR thật được thay bằng bản giả)."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from portal_docs_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    SECRET,
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

from src.config import Settings, get_settings
from src.model.document_version import DocumentVersion
from src.services.ingest.ocr import OcrError
from src.services.portal.job_service import JobContext

pytestmark = pytest.mark.integration


def pdf_bytes(*, with_text: bool) -> bytes:
    pymupdf: Any = __import__("pymupdf")
    document = pymupdf.open()
    page = document.new_page()
    if with_text:
        words = " ".join(f"chu{i}x{j}" for i in range(6) for j in range(10))
        page.insert_textbox(pymupdf.Rect(50, 50, 545, 790), words, fontsize=10, fontname="helv")
    return bytes(document.tobytes())


async def upload_scan(client: Any, category: str, source_key: str, label: str = "v1") -> Any:
    form = {**upload_form(category, source_key), "version_label": label, "effective_from": "2024-01-01"}
    return await client.post(
        "/api/v1/portal/documents",
        data=form,
        files={"file": ("scan.pdf", pdf_bytes(with_text=False), "application/pdf")},
    )


def ocr_context(job_ctx: JobContext, tmp_path: Path, fake: Any) -> JobContext:
    async def read_file(key: str) -> bytes:
        return (tmp_path / key).read_bytes()

    return replace(job_ctx, read_file=read_file, ocr_pdf=fake)


async def test_scan_upload_is_rejected_when_ocr_is_off(
    app: FastAPI, team: SimpleNamespace, category: str, make_member: MakeMember, cleanup_documents: list[str]
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ocr-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, session_secret=SECRET, ocr_enabled=False)
    async with client_for(app) as client:
        await login(client, hr)
        response = await upload_scan(client, category, source_key)
        assert response.status_code == 422 and response.json()["code"] == "INGEST_FAILED"


async def test_scan_upload_runs_ocr_in_background_and_unlocks_the_draft(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    tmp_path: Path,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ocr-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, session_secret=SECRET, ocr_enabled=True)

    async def fake_ocr(pdf: bytes) -> bytes:
        assert pdf[:4] == b"%PDF"
        return pdf_bytes(with_text=True)

    ctx = ocr_context(job_ctx, tmp_path, fake_ocr)
    async with client_for(app) as client:
        await login(client, hr)
        response = await upload_scan(client, category, source_key)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["job_id"] is not None
        version_id = body["document_version_id"]

        # Trong lúc chờ OCR: bản nháp bị khóa (PROCESSING), chưa có chữ.
        async with session_factory() as session:
            pending = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            assert pending is not None and pending.status == "PROCESSING" and pending.markdown == ""

        await run_jobs(ctx)
        job = (await client.get(f"/api/v1/portal/jobs/{body['job_id']}")).json()
        assert job["status"] == "SUCCEEDED", job

        detail = (await client.get(f"/api/v1/portal/documents/{body['document_id']}/versions/{version_id}")).json()
        assert detail["version"]["ocr"] is True and detail["version"]["state"] == "DRAFT"
        assert "chu3x4" in detail["markdown"]

    async with session_factory() as session:
        done = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
        assert done is not None and done.parser == "markitdown+ocr" and done.status == "DRAFT"
        assert done.quality_report["ocr"]["engine"] == "tesseract"


async def test_failed_ocr_returns_the_draft_with_a_reason_so_hr_can_delete_it(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    tmp_path: Path,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ocr-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, session_secret=SECRET, ocr_enabled=True)

    async def broken_ocr(pdf: bytes) -> bytes:
        raise OcrError("quá nhiều trang")

    ctx = ocr_context(job_ctx, tmp_path, broken_ocr)
    async with client_for(app) as client:
        await login(client, hr)
        body = (await upload_scan(client, category, source_key)).json()
        await run_jobs(ctx)
        job = (await client.get(f"/api/v1/portal/jobs/{body['job_id']}")).json()
        assert job["status"] == "FAILED"

        detail = (
            await client.get(f"/api/v1/portal/documents/{body['document_id']}/versions/{body['document_version_id']}")
        ).json()
        assert detail["version"]["state"] == "DRAFT" and "OCR" in (detail["version"]["failure_reason"] or "")
        deleted = await client.delete(
            f"/api/v1/portal/documents/{body['document_id']}/versions/{body['document_version_id']}"
        )
        assert deleted.status_code == 204
