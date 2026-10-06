"""Tài liệu thiếu heading chạy qua toàn luồng (tải nháp -> cảnh báo -> kích hoạt nền -> LLM chia mục) trên PostgreSQL thật.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 13. Có thêm các file Word thật của ngày 1 trong
`docs/chatbot-vsf/data/documents/day1/` (bản có heading và bản không heading, cùng nội dung).
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
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
    upload_form,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.llm_call import LlmCall
from src.services.portal.job_service import JobContext

pytestmark = pytest.mark.integration

DAY1 = Path(__file__).resolve().parents[3] / "docs" / "chatbot-vsf" / "data" / "documents" / "day1"
LINES = "\n".join(
    f"Dòng số {i} của một hướng dẫn dài không có tiêu đề nào cả, chỉ có chữ liền nhau." for i in range(60)
)


def splitting_llm(calls: list[int] | None = None) -> FakeChatCompletion:
    """LLM giả chọn 3 đoạn làm đầu mục (đoạn 1, một phần ba, hai phần ba)."""

    def respond(_system: str, user: str) -> str:
        if calls is not None:
            calls.append(1)
        total = len(re.findall(r"^§\d+ ", user, flags=re.MULTILINE))
        picks = sorted({1, max(2, total // 3), max(3, 2 * total // 3)})
        titles = ["Mở đầu", "Phần giữa", "Phần cuối"]
        headings = [{"paragraph": p, "level": 1, "title": titles[i]} for i, p in enumerate(picks)]
        return json.dumps({"headings": headings}, ensure_ascii=False)

    return FakeChatCompletion(respond)


def with_llm(ctx: JobContext, llm: FakeChatCompletion, **overrides: Any) -> JobContext:
    return JobContext(
        session_factory=ctx.session_factory,
        embedding=ctx.embedding,
        storage=ctx.storage,
        make_llm=lambda: llm,
        **overrides,
    )


async def upload_file(
    client: httpx.AsyncClient,
    category: str,
    source_key: str,
    filename: str,
    content: bytes,
    *,
    label: str = "1.0",
    activate: bool = False,
) -> httpx.Response:
    form = {**upload_form(category, source_key), "version_label": label}
    if activate:
        form["activate"] = "true"
    return await client.post("/api/v1/portal/documents", data=form, files={"file": (filename, content, "text/plain")})


async def section_titles(factory: async_sessionmaker[AsyncSession], version_id: int) -> list[str | None]:
    async with factory() as session:
        rows = await session.scalars(
            select(DocumentSection.heading)
            .where(DocumentSection.version_id == version_id)
            .order_by(DocumentSection.section_index)
        )
        return list(rows.all())


async def test_bold_titles_are_inferred_at_upload_and_visible_to_hr_before_activation(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    key = f"st-{uuid4().hex[:8]}"
    cleanup_documents.append(key)
    body = "**Hồ sơ cần nộp**\n\n" + "Nộp đủ giấy tờ theo danh sách tại phòng nhân sự. " * 10
    body += "\n\n**Nhận thiết bị**\n\n" + "Nhận laptop tại tầng 12 và đăng nhập Outlook. " * 10

    async with client_for(app) as client:
        await login(client, hr)
        response = await upload_file(client, category, key, "bold.md", body.encode("utf-8"))
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["structure_quality"] == "MEDIUM"
        assert data["structure_warnings"] == ["HEADINGS_INFERRED"]

        detail = (
            await client.get(f"/api/v1/portal/documents/{data['document_id']}/versions/{data['document_version_id']}")
        ).json()
        assert "## Hồ sơ cần nộp" in detail["markdown"]  # HR thấy và sửa được tiêu đề đã suy ra
        assert detail["version"]["structure_quality"] == "MEDIUM"


async def test_poor_structure_is_flagged_then_ai_splits_it_on_activation(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    key = f"st-{uuid4().hex[:8]}"
    cleanup_documents.append(key)
    calls: list[int] = []

    async with client_for(app) as client:
        await login(client, hr)
        response = await upload_file(client, category, key, "dai.md", LINES.encode("utf-8"), activate=True)
        data = response.json()
        assert data["structure_quality"] == "POOR"
        assert "NO_STRUCTURE" in data["structure_warnings"]

        await run_jobs(with_llm(job_ctx, splitting_llm(calls)))
        job = (await client.get(f"/api/v1/portal/jobs/{data['job_id']}")).json()
        assert job["status"] == "SUCCEEDED", job
        assert len(calls) == 1

        rows = (await client.get(f"/api/v1/portal/documents/{data['document_id']}/versions")).json()
        assert rows[0]["ai_split"] == "APPLIED"
        assert rows[0]["structure_quality"] == "GOOD"  # từ POOR lên GOOD nhờ AI chỉ ra tiêu đề

    titles = await section_titles(session_factory, data["document_version_id"])
    assert titles == ["Mở đầu", "Phần giữa", "Phần cuối"]
    async with session_factory() as session:
        version = await session.get(DocumentVersion, data["document_version_id"])
        assert version is not None
        # Chữ của tài liệu không đổi: bỏ các dòng heading do AI chèn thì phải y hệt bản gốc.
        kept = [line for line in version.markdown.splitlines() if not line.startswith("# ")]
        assert kept == LINES.splitlines()


async def test_invalid_ai_answer_falls_back_to_rule_based_result(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    key = f"st-{uuid4().hex[:8]}"
    cleanup_documents.append(key)

    async with client_for(app) as client:
        await login(client, hr)
        data = (await upload_file(client, category, key, "dai.md", LINES.encode("utf-8"), activate=True)).json()
        await run_jobs(with_llm(job_ctx, FakeChatCompletion("không phải json")))
        job = (await client.get(f"/api/v1/portal/jobs/{data['job_id']}")).json()
        assert job["status"] == "SUCCEEDED", job  # AI hỏng không bao giờ làm kích hoạt thất bại
        rows = (await client.get(f"/api/v1/portal/documents/{data['document_id']}/versions")).json()
        assert rows[0]["ai_split"] == "SKIPPED"

    assert len(await section_titles(session_factory, data["document_version_id"])) >= 1


async def test_ai_split_respects_switch_and_daily_limit(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    key_a, key_b = f"st-{uuid4().hex[:8]}", f"st-{uuid4().hex[:8]}"
    cleanup_documents.extend([key_a, key_b])
    calls: list[int] = []

    async with client_for(app) as client:
        await login(client, hr)
        a = (await upload_file(client, category, key_a, "a.md", LINES.encode("utf-8"), activate=True)).json()
        await run_jobs(with_llm(job_ctx, splitting_llm(calls), structure_llm_enabled=False))
        b = (
            await upload_file(client, category, key_b, "b.md", LINES.encode("utf-8"), label="2.0", activate=True)
        ).json()
        await run_jobs(with_llm(job_ctx, splitting_llm(calls), structure_llm_daily_limit=0))

        for data in (a, b):
            job = (await client.get(f"/api/v1/portal/jobs/{data['job_id']}")).json()
            assert job["status"] == "SUCCEEDED", job
    assert calls == []  # tắt công tắc hoặc hết hạn mức thì không gọi LLM

    async with session_factory() as session:
        used = await session.scalar(
            select(func.count()).select_from(LlmCall).where(LlmCall.operation == "ingest.structure")
        )
    assert not used  # chưa có lần gọi nào được ghi nhận


@pytest.mark.skipif(not DAY1.exists(), reason="thiếu thư mục dữ liệu ngày 1")
async def test_day1_docx_with_and_without_headings(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Hai file Word thật cùng nội dung: bản có heading chia đúng mục; bản không heading được luật cố định suy ra tiêu đề.

    Bản không heading của ngày 1 có sẵn các dòng tiêu đề viết HOA ("ZTNA", "CÁCH VIẾT EMAIL HỖ TRỢ ITHD"...), nên bậc 2
    nhận được 6 tiêu đề mà không cần AI: đúng thiết kế "rule-based trước, AI là phương án cuối".
    """
    with_headers = DAY1 / "Huong_dan_ngay_1_onboarding_co_header.docx"
    without_headers = DAY1 / "Huong_dan_ngay_1_onboarding_khong_header.docx"
    if not (with_headers.exists() and without_headers.exists()):
        pytest.skip("thiếu file docx ngày 1")
    hr = await make_member("HR", team.id)
    key_a, key_b = f"st-{uuid4().hex[:8]}", f"st-{uuid4().hex[:8]}"
    cleanup_documents.extend([key_a, key_b])

    async with client_for(app) as client:
        await login(client, hr)
        a = (
            await upload_file(client, category, key_a, with_headers.name, with_headers.read_bytes(), activate=True)
        ).json()
        b = (
            await upload_file(
                client, category, key_b, without_headers.name, without_headers.read_bytes(), activate=True
            )
        ).json()
        assert a["structure_quality"] == "GOOD"
        assert b["structure_quality"] == "MEDIUM"
        assert b["structure_warnings"] == ["HEADINGS_INFERRED"]
        calls: list[int] = []
        await run_jobs(with_llm(job_ctx, splitting_llm(calls)))
        assert calls == []  # đã suy ra được tiêu đề bằng luật nên không tốn lần gọi LLM nào
        for data in (a, b):
            assert (await client.get(f"/api/v1/portal/jobs/{data['job_id']}")).json()["status"] == "SUCCEEDED"

    with_titles = await section_titles(session_factory, a["document_version_id"])
    without_titles = await section_titles(session_factory, b["document_version_id"])
    assert len(with_titles) >= 10  # bản có heading: mỗi mục một section
    assert len(without_titles) >= 5  # bản không heading: các dòng viết HOA thành tiêu đề
    assert "ZTNA" in without_titles
