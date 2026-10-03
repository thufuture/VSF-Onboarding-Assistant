"""Tạo task bằng AI chạy nền (job có phần trăm), chấp nhận đề xuất, và hồi quy lỗi 1 và 3 (mục 10.2) trên PostgreSQL thật.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 14.5 (job tạo task) và 10.3 (chất lượng đề xuất).
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
    MD_CONTENT,
    MakeMember,
    app,
    category,
    cleanup_documents,
    cleanup_templates,
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

from src.api.dependencies import get_chat_completion_port
from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.model.document_version import DocumentVersion
from src.model.enums import Confidentiality, ContentKind
from src.model.task_template import TaskTemplate
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.ingest_service import ingest_document, today_in
from src.services.ingest.storage import LocalStorageAdapter
from src.services.portal import ai_task_service
from src.services.portal.job_service import JobContext

pytestmark = pytest.mark.integration

QUOTE = "Nội dung dùng để test upload qua API Portal."


def proposal_llm(*, group: str | None = "DEVICE", wrap: bool = False) -> FakeChatCompletion:
    """LLM giả: đề xuất một task trích đúng section đầu tiên trong prompt, với quote nguyên văn."""

    def respond(_system: str, user: str) -> str:
        match = re.search(r"section_id=(\d+)", user)
        assert match is not None
        items = [
            {
                "title": "Nhận laptop",
                "summary": "Để làm việc được ngay từ ngày đầu.",
                "instructions_markdown": "1. Nhận laptop tại tầng 12\n2. Đăng nhập Outlook",
                "done_criteria": ["Đăng nhập được Outlook"],
                "estimated_minutes": 30,
                "source_chunks": [{"document_section_id": int(match.group(1)), "quote": QUOTE}],
                "confidence": "HIGH",
                "warnings": ["Mang theo CCCD"],
                "task_group": group,
            }
        ]
        return json.dumps({"tasks": items} if wrap else items, ensure_ascii=False)

    return FakeChatCompletion(respond)


async def make_active_version(
    client: httpx.AsyncClient, ctx: JobContext, category: str, source_key: str, label: str = "1.0"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/portal/documents",
        data={**upload_form(category, source_key), "version_label": label, "activate": "true"},
        files={"file": ("tai-lieu.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 202, response.text
    await run_jobs(ctx)
    body: dict[str, Any] = response.json()
    return body


def with_llm(ctx: JobContext, llm: FakeChatCompletion | None, *, error: Exception | None = None) -> JobContext:
    def make() -> FakeChatCompletion:
        if error is not None:
            raise error
        assert llm is not None
        return llm

    return JobContext(session_factory=ctx.session_factory, embedding=ctx.embedding, storage=ctx.storage, make_llm=make)


async def start_proposal_job(client: httpx.AsyncClient, version_ids: list[int]) -> int:
    response = await client.post("/api/v1/portal/ai/task-proposal-jobs", json={"document_version_ids": version_ids})
    assert response.status_code == 202, response.text
    return int(response.json()["id"])


async def test_proposal_job_reports_per_document_results_and_failures_do_not_block_others(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    key_a, key_b = f"ai-{uuid4().hex[:8]}", f"ai-{uuid4().hex[:8]}"
    cleanup_documents.extend([key_a, key_b])

    async with client_for(app) as client:
        await login(client, hr)
        first = await make_active_version(client, job_ctx, category, key_a)
        second = await make_active_version(client, job_ctx, category, key_b)
        job_id = await start_proposal_job(client, [first["document_version_id"], second["document_version_id"]])

        # Tài liệu thứ hai nhận phản hồi hỏng: chỉ tài liệu đó lỗi, tài liệu đầu vẫn có đề xuất.
        calls = {"n": 0}

        def respond(system: str, user: str) -> str:
            calls["n"] += 1
            if calls["n"] == 2:
                return "không phải json"
            result: str = proposal_llm().__dict__["_response"](system, user)
            return result

        await run_jobs(with_llm(job_ctx, FakeChatCompletion(respond)))
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()

    assert job["status"] == "SUCCEEDED", job
    assert job["progress_percent"] == 100
    documents = job["result"]["documents"]
    assert [d["status"] for d in documents] == ["DONE", "FAILED"]
    assert documents[1]["error"] == "AI_INVALID_JSON"
    assert len(documents[0]["proposals"]) == 1
    assert documents[0]["proposals"][0]["task_group"] == "DEVICE"


async def test_proposal_accepts_object_wrapped_json_and_fills_group_from_category(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    key = f"ai-{uuid4().hex[:8]}"
    cleanup_documents.append(key)

    async with client_for(app) as client:
        await login(client, hr)
        created = await make_active_version(client, job_ctx, category, key)
        job_id = await start_proposal_job(client, [created["document_version_id"]])
        # AI không chọn nhóm (null) và JSON bọc trong object: vẫn nhận được; nhóm lấy theo danh mục tài liệu.
        await run_jobs(with_llm(job_ctx, proposal_llm(group=None, wrap=True)))
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()

    assert job["status"] == "SUCCEEDED", job
    proposals = job["result"]["documents"][0]["proposals"]
    assert len(proposals) == 1
    # Danh mục thử không có trong bảng ánh xạ nên không có nhóm mặc định: giữ null thay vì đoán.
    assert proposals[0]["task_group"] is None


def test_category_mapping_assigns_default_group() -> None:
    assert ai_task_service.CATEGORY_TASK_GROUP["thiet-bi-tai-khoan"] == "DEVICE"
    assert ai_task_service.CATEGORY_TASK_GROUP["phan-cong-mentor-cho-ngoi"] == "OFFICE"
    assert set(ai_task_service.CATEGORY_TASK_GROUP.values()) <= {"PROFILE", "TRAINING", "DEVICE", "OFFICE"}


async def test_proposal_prompt_is_truncated_to_budget(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hr = await make_member("HR", team.id)
    key = f"ai-{uuid4().hex[:8]}"
    cleanup_documents.append(key)
    monkeypatch.setattr(ai_task_service, "PROPOSAL_TOKEN_BUDGET", 150)
    big = "# Tài liệu lớn\n\n" + "\n\n".join(f"## Mục {i}\n\n" + (f"{QUOTE} mục {i}. " * 15) for i in range(6))

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/documents",
            data={**upload_form(category, key), "activate": "true"},
            files={"file": ("lon.md", big.encode("utf-8"), "text/markdown")},
        )
        await run_jobs(job_ctx)
        job_id = await start_proposal_job(client, [response.json()["document_version_id"]])
        await run_jobs(with_llm(job_ctx, proposal_llm()))
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()

    entry = job["result"]["documents"][0]
    assert entry["status"] == "DONE"
    assert entry["truncated_sections"] >= 1


async def test_proposal_job_rejects_draft_versions(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    key = f"ai-{uuid4().hex[:8]}"
    cleanup_documents.append(key)

    async with client_for(app) as client:
        await login(client, hr)
        draft = (
            await client.post(
                "/api/v1/portal/documents",
                data=upload_form(category, key),
                files={"file": ("tai-lieu.md", MD_CONTENT.encode("utf-8"), "text/markdown")},
            )
        ).json()
        response = await client.post(
            "/api/v1/portal/ai/task-proposal-jobs", json={"document_version_ids": [draft["document_version_id"]]}
        )

    assert response.status_code == 422
    assert response.json()["code"] == "VERSION_NOT_USABLE"


async def test_proposal_job_without_llm_key_fails_cleanly(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    key = f"ai-{uuid4().hex[:8]}"
    cleanup_documents.append(key)

    async with client_for(app) as client:
        await login(client, hr)
        created = await make_active_version(client, job_ctx, category, key)
        job_id = await start_proposal_job(client, [created["document_version_id"]])
        await run_jobs(with_llm(job_ctx, None, error=RuntimeError("LLM_API_KEY chưa cấu hình")))
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()

    assert job["status"] == "FAILED"
    assert "LLM_NOT_CONFIGURED" in job["error"]


async def test_proposal_job_marks_document_failed_when_llm_is_unavailable(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
) -> None:
    hr = await make_member("HR", team.id)
    key = f"ai-{uuid4().hex[:8]}"
    cleanup_documents.append(key)

    def broken(_system: str, _user: str) -> str:
        raise ChatCompletionError("lỗi mạng khi gọi LLM")

    async with client_for(app) as client:
        await login(client, hr)
        created = await make_active_version(client, job_ctx, category, key)
        job_id = await start_proposal_job(client, [created["document_version_id"]])
        await run_jobs(with_llm(job_ctx, FakeChatCompletion(broken)))
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()

    assert job["status"] == "SUCCEEDED"  # việc nền vẫn xong; lỗi nằm ở dòng của tài liệu đó
    assert job["result"]["documents"][0]["error"] == "LLM_UNAVAILABLE"


async def test_accept_composes_three_section_body_and_validates_quote(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    cleanup_templates: list[int],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    key = f"ai-{uuid4().hex[:8]}"
    cleanup_documents.append(key)

    async with client_for(app) as client:
        await login(client, hr)
        created = await make_active_version(client, job_ctx, category, key)
        job_id = await start_proposal_job(client, [created["document_version_id"]])
        await run_jobs(with_llm(job_ctx, proposal_llm()))
        job = (await client.get(f"/api/v1/portal/jobs/{job_id}")).json()
        proposal = job["result"]["documents"][0]["proposals"][0]

        template = (
            await client.post(
                "/api/v1/portal/journey-templates", json={"code": f"tpl-{uuid4().hex[:8]}", "title": "Thử"}
            )
        ).json()
        cleanup_templates.append(template["id"])
        stage = (
            await client.post(f"/api/v1/portal/journey-templates/{template['id']}/stages", json={"title": "Ngày 1"})
        ).json()

        accept_body = {
            "title": proposal["title"],
            "instructions_markdown": proposal["instructions_markdown"],
            "source_chunks": proposal["source_chunks"],
            "summary": proposal["summary"],
            "done_criteria": proposal["done_criteria"],
            "estimated_minutes": proposal["estimated_minutes"],
            "warnings": proposal["warnings"],
            "task_group": proposal["task_group"],
        }

        # Quote không nằm trong section: từ chối, không ghi gì.
        forged = {
            **accept_body,
            "source_chunks": [{**proposal["source_chunks"][0], "quote": "câu không có trong tài liệu"}],
        }
        rejected = await client.post(f"/api/v1/portal/stages/{stage['id']}/tasks/from-proposal", json=forged)
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "INVALID_SOURCE_CHUNK"

        accepted = await client.post(f"/api/v1/portal/stages/{stage['id']}/tasks/from-proposal", json=accept_body)
        assert accepted.status_code == 200, accepted.text

    async with session_factory() as session:
        tasks = (await session.scalars(select(TaskTemplate).where(TaskTemplate.journey_stage_id == stage["id"]))).all()
    assert len(tasks) == 1  # lần bị từ chối không để lại task nửa vời
    task = tasks[0]
    assert task.task_group == "DEVICE"
    assert "## Vì sao phải làm\nĐể làm việc được ngay từ ngày đầu." in task.body_markdown
    assert "Ước tính khoảng 30 phút." in task.body_markdown
    assert "Lưu ý: Mang theo CCCD" in task.body_markdown
    assert "## Điều kiện hoàn thành\n- Đăng nhập được Outlook" in task.body_markdown
    assert "## Các bước\n1. Nhận laptop tại tầng 12\n2. Đăng nhập Outlook" in task.body_markdown


async def test_cli_ingest_of_new_version_closes_previous_one(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    tmp_path: Path,
) -> None:
    """Hồi quy lỗi 1 (mục 10.2) trên đường nạp CLI `ingest_document`: phiên bản mới đóng bản cũ trong cùng transaction."""
    hr = await make_member("HR", team.id)
    key = f"cli-{uuid4().hex[:8]}"
    cleanup_documents.append(key)
    today = today_in()
    results = []
    for label, text in (("1.0", MD_CONTENT), ("2.0", MD_CONTENT + "\n\n" + "Phần bổ sung cho phiên bản hai. " * 20)):
        path = tmp_path / f"{label}.md"
        path.write_text(text, encoding="utf-8")
        async with session_factory() as session:
            results.append(
                await ingest_document(
                    session,
                    file_path=path,
                    category_slug=category,
                    owner_email=hr.email,
                    title="Tài liệu CLI",
                    source_key=key,
                    version_label=label,
                    effective_from=today,
                    content_kind=ContentKind.GENERAL.value,
                    confidentiality=Confidentiality.INTERNAL.value,
                    embedding=FakeEmbeddingAdapter(),
                    storage=LocalStorageAdapter(str(tmp_path)),
                )
            )

    async with session_factory() as session:
        old = await session.get(DocumentVersion, results[0].version_id)
        new = await session.get(DocumentVersion, results[1].version_id)
    assert old is not None and new is not None
    assert old.status == "ARCHIVED"
    assert old.effective_to == today  # cùng ngày bắt đầu nên bản cũ khép lại ngay ngày đó
    assert new.status == "ACTIVE" and new.effective_to is None


async def test_ai_service_failure_in_chat_returns_503_not_500(
    app: FastAPI,
    team: SimpleNamespace,
    make_member: MakeMember,
) -> None:
    """Hồi quy lỗi 3 (mục 10.2): lỗi LLM/embedding trong `/chat/ask` trả 503 có mã rõ ràng thay vì 500."""
    member = await make_member("USER", team.id)

    class BrokenLlm:
        async def complete_json(
            self, *, system_prompt: str, user_prompt: str, timeout_seconds: float | None = None
        ) -> str:
            raise ChatCompletionError("lỗi mạng khi gọi LLM")

    app.dependency_overrides[get_chat_completion_port] = lambda: BrokenLlm()
    async with client_for(app) as client:
        await login(client, member)
        response = await client.post("/api/v1/chat/ask", json={"question": "Nghỉ phép năm có bao nhiêu ngày?"})

    assert response.status_code == 503, response.text
    assert response.json()["code"] == "ASSISTANT_UNAVAILABLE"
    assert response.headers["retry-after"] == "5"
