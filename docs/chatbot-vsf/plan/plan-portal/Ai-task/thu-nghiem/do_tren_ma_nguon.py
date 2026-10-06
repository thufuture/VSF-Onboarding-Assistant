# -*- coding: utf-8 -*-
"""Đo MÃ NGUỒN THẬT của "Tạo task bằng AI" (không phải kịch bản thử): gọi `ai_task_service.propose_tasks_detailed` với adapter
DeepSeek thật, đường cũ (legacy) và đường nhanh (fast), rồi chấm các chỉ số chất lượng tự động (cổng chất lượng, kế hoạch mục 14.6).
Không ghi DB: các mục lấy từ file JSON trong thư mục này (tài liệu mẫu công khai trong repo).

    python do_tren_ma_nguon.py <ten-tai-lieu> <legacy|fast> <số-lần> <số-lần-chạy-song-song> <tên-file-kết-quả>

    ten-tai-lieu:  ngay1 (16 mục) | ngoai-le (22 mục) | docx-ngay1 (file Huong_dan_ngay_1_onboarding.docx, đọc và cắt mục đúng như ingest: 3 mục có tiêu đề suy ra)

Cần backend venv và khóa LLM trong `.env` gốc repo (khóa không bao giờ được in ra).
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / "backend"))

from src.infrastructure.ai.deepseek_adapter import ChatCompletionError, DeepSeekChatCompletion  # noqa: E402
from src.infrastructure.ai.llm_gate import LlmGate  # noqa: E402
from src.infrastructure.observability.call_metrics import call_context, collect_calls, set_prices  # noqa: E402
from src.services.portal import ai_task_service as svc  # noqa: E402
from src.services.portal.proposal_options import ProposalOptions  # noqa: E402
from src.services.text_match import normalize_for_match, quote_matches  # noqa: E402

DOCS = {"ngay1": "huong_dan_ngay_1_sections.json", "ngoai-le": "cac_truong_hop_ngoai_le_sections.json", "docx-ngay1": None}
DOCX_PATH = ROOT / "docs" / "chatbot-vsf" / "data" / "documents" / "day1" / "Huong_dan_ngay_1_onboarding.docx"
FACTS = {
    "ngay1": ["tầng 12", "tầng 14", "80%", "v.thudq@vinsmartfuture.tech", "support@vinsmartfuture.tech", "phòng tuyển dụng",
              "quick access", "t3", "vinsoc", "outlook", "ngannk25", "ducbv5", "ubuntu", "cuối ngày", "helpdesk"],
    "ngoai-le": [],
    "docx-ngay1": [],
}


def env(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"thiếu {name} trong .env")


class _Rows:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _Session:
    def __init__(self, sections):
        self._sections = sections

    async def scalars(self, _q):
        return _Rows(self._sections)

    async def scalar(self, _q):
        return "onboarding"


def load(doc: str):
    if doc == "docx-ngay1":  # đúng đường của ingest: đọc docx -> Markdown -> cắt mục
        from src.services.ingest.ingest_service import chunk_markdown  # noqa: E402
        from src.services.ingest.parser import parse_document  # noqa: E402

        from src.services.ingest.structure import analyze_structure  # noqa: E402

        parsed = parse_document(DOCX_PATH)
        markdown, _ = analyze_structure(parsed.markdown)  # như ingest thật: file không tiêu đề được suy ra tiêu đề (3 mục)
        drafts = [section for section, _ in chunk_markdown(markdown)[0]]
        return [
            SimpleNamespace(id=100 + i, section_index=d.section_index, heading=d.heading, content=d.content, token_count=d.token_count)
            for i, d in enumerate(drafts)
        ]
    raw = json.loads((HERE / DOCS[doc]).read_text(encoding="utf-8"))
    return [
        SimpleNamespace(id=s["id"], section_index=s["idx"], heading=s["heading"], content=s["content"],
                        token_count=max(1, len(s["content"].split())))
        for s in raw
    ]


def judge(doc: str, sections, result) -> dict:
    """Các chỉ số tự động của cổng chất lượng (không thay thế được so sánh mù do người chấm)."""
    by_id = {s.id: s for s in sections}
    proposals = result.proposals
    cited = {c.document_section_id for p in proposals for c in p.source_chunks}
    coverable = [s for s in sections if len(svc.section_text(s).strip()) >= svc.MIN_COVERABLE_CHARS]
    quotes_ok = all(
        quote_matches(c.quote, svc.section_text(by_id[c.document_section_id])) for p in proposals for c in p.source_chunks
    )
    text = " ".join(
        normalize_for_match(" ".join([p.title, p.summary, p.instructions_markdown, *p.done_criteria])) for p in proposals
    )
    facts = FACTS[doc]
    titles = [p.title for p in proposals]
    position = {p.title: i for i, p in enumerate(proposals)}
    deps_valid = all(position[name] < position[p.title] for p in proposals for name in p.prerequisites if name in position)
    return {
        "tasks": len(proposals),
        "covered": f"{len(cited & {s.id for s in coverable})}/{len(coverable)}",
        "uncovered_reported": len(result.uncovered),
        "facts": f"{sum(1 for f in facts if normalize_for_match(f) in text)}/{len(facts)}" if facts else "n/a",
        "quotes_all_verbatim": quotes_ok,
        "dependencies": sum(len(p.prerequisites) for p in proposals),
        "dependencies_point_backwards_only": deps_valid,
        # Việc gắn với "cuối ngày" phải đứng sau mọi việc khác; None nếu tài liệu không có việc nào như vậy.
        "end_of_day_after_others": (
            None
            if not any(svc._is_end_of_day(p) for p in proposals)
            else all(svc._is_end_of_day(p) for p in proposals[[svc._is_end_of_day(q) for q in proposals].index(True) :])
        ),
        "low_confidence": sum(1 for p in proposals if p.confidence == "LOW"),
        "tasks_with_review_notes": sum(1 for p in proposals if p.review_notes),
        "empty_steps": sum(1 for p in proposals if not p.instructions_markdown.strip()),
        "duplicate_titles": len(titles) - len({normalize_for_match(t) for t in titles}),
        "order_source": result.order_source,
        "skipped_sections": len(result.skipped_info),
        "batches": result.batches,
    }


async def one_run(doc: str, mode: str, llm, sections) -> tuple[dict, list]:
    options = ProposalOptions(mode=mode)  # type: ignore[arg-type]
    started = time.perf_counter()
    error = None
    result = None
    with collect_calls() as calls:
        try:
            with call_context(operation="job", job_id=1):  # như khi chạy trong job: lời gọi thuộc nhóm "nền" của bộ giới hạn
                result = await svc.propose_tasks_detailed(_Session(sections), document_version_id=1, llm=llm, options=options)  # type: ignore[arg-type]
        except (ChatCompletionError, svc.PortalError) as exc:
            error = type(exc).__name__ + ": " + str(getattr(exc, "code", exc))[:60]
    seconds = time.perf_counter() - started
    row: dict = {
        "mode": mode, "seconds": round(seconds, 1), "llm_calls": len(calls.calls), "tokens_in": calls.prompt_tokens,
        "tokens_out": calls.completion_tokens, "tokens_reasoning": sum(c.reasoning_tokens for c in calls.calls),
        "retries": sum(1 for c in calls.calls if not c.ok), "max_queue_wait_ms": round(max((c.queue_wait_ms or 0) for c in calls.calls)),
    }
    if error or result is None:
        row["error"] = error
        return row, []
    row.update(judge(doc, sections, result))
    row["step_seconds"] = result.timings
    row["cost_usd"] = round(calls.cost_usd, 5)
    detail = [
        {"order": p.order, "title": p.title, "summary": p.summary, "steps": p.instructions_markdown.split("\n"),
         "done_criteria": p.done_criteria, "prerequisites": p.prerequisites, "sources": [c.document_section_id for c in p.source_chunks],
         "review_notes": p.review_notes, "confidence": p.confidence}
        for p in result.proposals
    ]
    return row, detail


async def main() -> None:
    doc, mode, runs, parallel, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    sections = load(doc)
    set_prices(llm_input_per_million=0.30, llm_output_per_million=1.20, embedding_per_thousand=0.0)
    gate = LlmGate(9, 5)
    llm = DeepSeekChatCompletion(base_url=env("LLM_BASE_URL"), api_key=env("LLM_API_KEY"), model=env("LLM_MODEL"),
                                 max_retries=2, gate=gate)
    rows: list[dict] = []
    details: list[list] = []
    remaining = runs
    while remaining > 0:
        batch = min(parallel, remaining)
        remaining -= batch
        outcomes = await asyncio.gather(*(one_run(doc, mode, llm, sections) for _ in range(batch)))
        for row, detail in outcomes:
            rows.append(row)
            details.append(detail)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    payload = {"doc": doc, "sections": len(sections), "mode": mode, "parallel": parallel, "peak_in_flight": gate.peak, "runs": rows}
    (HERE / f"{out}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / f"{out}-chi-tiet.json").write_text(json.dumps(details, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
