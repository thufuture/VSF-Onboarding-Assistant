"""Chạy THẬT end-to-end: tải tài liệu mẫu (docx) -> kích hoạt -> job tạo task bằng AI với DeepSeek thật (đường nhanh) -> đọc tiến độ
mỗi 0,5 giây qua API như giao diện -> kiểm `llm_calls` có số đo từng pha. Ghi dòng thời gian vào thư mục thử nghiệm của kế hoạch.

Mặc định BỊ BỎ QUA (tốn một khoản phí nhỏ và cần khóa LLM). Chạy: đặt `VSF_REAL_LLM=1` cùng `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
và `VSF_TEST_DATABASE_URL` rồi `pytest tests/integration/test_portal_ai_task_real_llm.py -s`.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from portal_docs_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
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

from src.infrastructure.ai.deepseek_adapter import DeepSeekChatCompletion
from src.infrastructure.ai.llm_gate import LlmGate
from src.infrastructure.observability.call_metrics import set_prices, set_sink
from src.model.llm_call import LlmCall
from src.services.portal.job_service import JobContext
from src.services.portal.metrics_service import DbCallSink
from src.services.portal.proposal_options import ProposalOptions

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("VSF_REAL_LLM") != "1", reason="cần VSF_REAL_LLM=1 (gọi LLM thật, tốn phí nhỏ)"),
]

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "docs" / "chatbot-vsf" / "data" / "documents" / "day1"
OUT = ROOT / "docs" / "chatbot-vsf" / "plan" / "plan-portal" / "Ai-task" / "thu-nghiem"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def upload_sample(client: Any, ctx: JobContext, category: str, filename: str, key: str) -> int:
    response = await client.post(
        "/api/v1/portal/documents",
        data={**upload_form(category, key), "title": filename, "activate": "true"},
        files={"file": (filename, (SAMPLES / filename).read_bytes(), DOCX)},
    )
    assert response.status_code == 202, response.text
    await run_jobs(ctx)
    return int(response.json()["document_version_id"])


async def run_and_record(
    app_client: Any, job_id: int, ctx: JobContext, interval: float = 0.5
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Chạy job và đọc tiến độ qua API đều đặn như giao diện; trả (job cuối, dòng thời gian)."""
    timeline: list[dict[str, Any]] = []
    started = time.perf_counter()
    stop = asyncio.Event()

    async def poll() -> None:
        while not stop.is_set():
            job = (await app_client.get(f"/api/v1/portal/jobs/{job_id}")).json()
            steps = {s["key"]: s["status"] for s in (job.get("progress") or {}).get("steps", [])}
            timeline.append(
                {
                    "t": round(time.perf_counter() - started, 1),
                    "status": job["status"],
                    "percent": job["progress_percent"],
                    "elapsed_seconds": job["elapsed_seconds"],
                    "queue_ahead": job["queue_ahead"],
                    "steps": steps,
                }
            )
            try:
                await asyncio.wait_for(stop.wait(), interval)
            except TimeoutError:
                pass

    poller = asyncio.create_task(poll())
    await run_jobs(ctx)
    stop.set()
    await poller
    final: dict[str, Any] = (await app_client.get(f"/api/v1/portal/jobs/{job_id}")).json()
    steps = {s["key"]: s["status"] for s in (final.get("progress") or {}).get("steps", [])}
    timeline.append(  # mẫu cuối sau khi job xong (lần hỏi cuối của giao diện)
        {
            "t": round(time.perf_counter() - started, 1),
            "status": final["status"],
            "percent": final["progress_percent"],
            "elapsed_seconds": final["elapsed_seconds"],
            "queue_ahead": final["queue_ahead"],
            "steps": steps,
        }
    )
    return final, timeline


def real_ctx(base: JobContext) -> JobContext:
    llm = DeepSeekChatCompletion(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_MODEL"],
        max_retries=2,
        gate=LlmGate(9, 5),
    )
    return JobContext(
        session_factory=base.session_factory,
        embedding=base.embedding,
        storage=base.storage,
        make_llm=lambda: llm,
        proposal=ProposalOptions(mode="fast"),
    )


async def test_real_job_one_document_three_times_then_two_documents_in_parallel(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    job_ctx: JobContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    keys = [f"real-{uuid4().hex[:8]}" for _ in range(2)]
    cleanup_documents.extend(keys)
    sink = DbCallSink(session_factory)
    set_prices(llm_input_per_million=0.30, llm_output_per_million=1.20, embedding_per_second=0.0)
    set_sink(sink)
    try:
        async with client_for(app) as client:
            await login(client, hr)
            first = await upload_sample(client, job_ctx, category, "Huong_dan_ngay_1_onboarding.docx", keys[0])
            second = await upload_sample(client, job_ctx, category, "Cac_truong_hop_ngoai_le_ngay_1_v2.docx", keys[1])
            ctx = real_ctx(job_ctx)

            results: dict[str, Any] = {}
            plan = [(f"mot-tai-lieu-{n}", [first]) for n in (1, 2, 3)] + [("hai-tai-lieu-song-song", [first, second])]
            for name, versions in plan:
                response = await client.post(
                    "/api/v1/portal/ai/task-proposal-jobs", json={"document_version_ids": versions}
                )
                assert response.status_code == 202, response.text
                job_id = int(response.json()["id"])
                job, timeline = await run_and_record(client, job_id, ctx)
                assert job["status"] == "SUCCEEDED", job
                results[name] = {"job_id": job_id, "job": job, "timeline": timeline}
                documents = job["result"]["documents"]
                assert all(d["status"] == "DONE" and d["proposals"] for d in documents), documents
                assert all(d["metrics"]["mode"] == "fast" for d in documents)
                percents = [row["percent"] for row in timeline]
                assert percents == sorted(percents), "phần trăm không được giảm"
                assert percents[-1] == 100
                assert any(0 < p < 100 for p in percents), "phải có số đo giữa chừng, không nhảy thẳng 0 -> 100"
                assert {row["steps"].get("draft") for row in timeline} >= {"running", "done"}

            await sink.drain()
    finally:
        set_sink(None)

    async with session_factory() as session:
        calls = (
            await session.scalars(
                select(LlmCall).where(LlmCall.job_id.in_([r["job_id"] for r in results.values()])).order_by(LlmCall.id)
            )
        ).all()
    assert calls and all(c.operation == "task.proposal" for c in calls)
    assert all(c.finish_reason == "stop" and c.first_token_ms is not None for c in calls if c.ok)
    assert all(c.reasoning_tokens == 0 for c in calls if c.ok), "đã tắt suy luận: không còn token suy luận"
    payload = {
        "ghi_chu": "Chạy thật end-to-end (API -> job -> DeepSeek thật). Dòng thời gian đọc qua GET /portal/jobs/{id} mỗi 0,5 giây.",
        "scenarios": {
            name: {
                "job_id": r["job_id"],
                "elapsed_seconds": r["job"]["elapsed_seconds"],
                "documents": [
                    {
                        "title": d["document_title"],
                        "tasks": len(d["proposals"]),
                        "uncovered": len(d.get("uncovered_sections") or []),
                        "skipped_info": len(d.get("skipped_info_sections") or []),
                        "metrics": d["metrics"],
                        "titles": [p["title"] for p in d["proposals"]],
                    }
                    for d in r["job"]["result"]["documents"]
                ],
                "timeline": r["timeline"],
            }
            for name, r in results.items()
        },
        "llm_calls": [
            {
                "id": c.id,
                "job_id": c.job_id,
                "ok": c.ok,
                "attempt": c.attempt,
                "latency_ms": round(c.latency_ms),
                "queue_wait_ms": round(c.queue_wait_ms or 0),
                "first_byte_ms": round(c.first_byte_ms or 0),
                "first_token_ms": round(c.first_token_ms or 0),
                "reasoning_ms": round(c.reasoning_ms or 0),
                "content_ms": round(c.content_ms or 0),
                "prompt_tokens": c.prompt_tokens,
                "completion_tokens": c.completion_tokens,
                "reasoning_tokens": c.reasoning_tokens,
                "cached_input_tokens": c.cached_input_tokens,
                "finish_reason": c.finish_reason,
                "cost_usd": round(c.cost_usd, 5),
            }
            for c in calls
        ],
    }
    (OUT / "ket-qua-11-job-that-tren-db.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
