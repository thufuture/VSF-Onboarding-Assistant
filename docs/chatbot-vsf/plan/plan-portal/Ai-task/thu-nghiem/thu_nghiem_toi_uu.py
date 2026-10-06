# -*- coding: utf-8 -*-
"""Đo thời gian "Tạo task bằng AI" và thử các cách tối ưu. CHỈ ĐO: không sửa mã sản phẩm, không ghi DB.

Dùng (cần backend venv, khóa LLM trong `.env` gốc repo; khóa không bao giờ được in ra):

    python thu_nghiem_toi_uu.py so-sanh        # A: hiện trạng, B: tắt suy luận, C: 4 nhóm song song, D: 4 nhóm song song + tắt suy luận
    python thu_nghiem_toi_uu.py tat-suy-luan   # một lời gọi tắt suy luận, 5 lần song song: độ ổn định
    python thu_nghiem_toi_uu.py chia-nhom      # phương án đề xuất: 4 nhóm song song, tắt suy luận, trích bằng số dòng, bù phủ, xếp thứ tự
    python thu_nghiem_toi_uu.py mot-loi-goi    # như trên nhưng chỉ MỘT lời gọi cho cả tài liệu (không chia nhóm)
    python thu_nghiem_toi_uu.py stream-do-cham # đo từng pha (chờ đầu tiên, suy luận, viết JSON) của một lời gọi bằng stream

Dữ liệu: 16 mục của "Hướng dẫn ngày 1" (huong_dan_ngay_1_sections.json, lấy từ tài liệu mẫu trong repo). Kết quả thô ghi cạnh script.
"""
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / "backend"))
from src.services.portal import ai_task_service as svc  # noqa: E402  (lời nhắc và bộ lọc đang dùng thật)
from src.services.text_match import normalize_for_match  # noqa: E402


def env(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"thiếu {name} trong .env")


BASE, MODEL, KEY = env("LLM_BASE_URL"), env("LLM_MODEL"), env("LLM_API_KEY")
# Mặc định: 16 mục của "Hướng dẫn ngày 1". Đặt TN_SECTIONS=cac_truong_hop_ngoai_le_sections.json (và TN_SUFFIX=ngoai-le) để thử tài liệu 22 mục.
RAW = json.loads((HERE / os.environ.get("TN_SECTIONS", "huong_dan_ngay_1_sections.json")).read_text(encoding="utf-8"))
SECTIONS = [
    SimpleNamespace(id=s["id"], section_index=s["idx"], heading=s["heading"], content=s["content"], token_count=max(1, len(s["content"]) // 3))
    for s in RAW
]
BY_ID = {s.id: s for s in SECTIONS}
# Các chi tiết thật trong tài liệu mà bộ task tốt phải giữ lại (đo độ đầy đủ nội dung một cách thô).
FACTS = ["tầng 12", "tầng 14", "80%", "v.thudq@vinsmartfuture.tech", "support@vinsmartfuture.tech", "phòng tuyển dụng", "quick access", "t3", "vinsoc",
         "outlook", "ngannk25", "ducbv5", "ubuntu", "cuối ngày", "helpdesk"]


# Nhà cung cấp giới hạn số lời gọi ĐỒNG THỜI của cả tài khoản (đo ngày 02/10/2026: 11, vượt thì trả HTTP 429). Script tự giữ tối đa 9
# lời gọi cùng lúc và thử lại khi gặp 429, để số đo không bị méo bởi giới hạn này.
_GATE = asyncio.Semaphore(9)


async def llm(system: str, user: str, *, thinking: bool) -> dict:
    body = {"model": MODEL, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "response_format": {"type": "json_object"}}
    if not thinking:
        body["thinking"] = {"type": "disabled"}
    started = time.perf_counter()
    response = None
    async with _GATE:
        for attempt in range(5):
            async with httpx.AsyncClient(timeout=400) as client:
                response = await client.post(f"{BASE.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, json=body)
            if response.status_code != 429:
                break
            await asyncio.sleep(1.5 * (attempt + 1))
    seconds = time.perf_counter() - started
    if response.status_code != 200:
        return {"ok": False, "seconds": seconds, "error": response.text[:150]}
    data = response.json()
    usage = data.get("usage", {})
    return {
        "ok": True, "seconds": seconds, "content": data["choices"][0]["message"].get("content") or "",
        "tin": usage.get("prompt_tokens", 0), "tout": usage.get("completion_tokens", 0),
        "reasoning": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
    }


def groups_of(n: int) -> list[list]:
    size = -(-len(SECTIONS) // n)
    return [SECTIONS[i : i + size] for i in range(0, len(SECTIONS), size)]


def save(name: str, payload: dict) -> None:
    if os.environ.get("TN_SUFFIX"):
        name = name.replace(".json", f"-{os.environ['TN_SUFFIX']}.json")
    (HERE / name).write_text(json.dumps({"model": MODEL, **payload}, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ so-sanh, tat-suy-luan (dùng lời nhắc hiện tại)
def evaluate_current(results: list[dict]) -> dict:
    proposals, raw_items = [], 0
    for r in results:
        if not r["ok"]:
            continue
        try:
            raw_items += len(svc._extract_items(json.loads(r["content"])))
        except Exception:
            continue
        proposals += svc._parse_proposals(r["content"], BY_ID, "PROFILE")
    cited = {c.document_section_id for p in proposals for c in p.source_chunks}
    text = normalize_for_match(" ".join(p.title + " " + p.summary + " " + p.instructions_markdown + " " + " ".join(p.done_criteria) for p in proposals))
    return {
        "calls": len(results), "wall_seconds": round(max(r["seconds"] for r in results), 1), "sum_seconds": round(sum(r["seconds"] for r in results), 1),
        "tokens_in": sum(r.get("tin", 0) for r in results), "tokens_out": sum(r.get("tout", 0) for r in results),
        "reasoning_tokens": sum(r.get("reasoning", 0) for r in results), "raw_items": raw_items, "valid_proposals": len(proposals),
        "sections_covered": f"{len({s.id for s in SECTIONS} & cited)}/{len(SECTIONS)}", "facts_found": f"{sum(1 for f in FACTS if normalize_for_match(f) in text)}/{len(FACTS)}",
        "per_call_seconds": [round(r["seconds"], 1) for r in results], "per_call_tokens_out": [r.get("tout", 0) for r in results],
        "per_call_reasoning": [r.get("reasoning", 0) for r in results],
    }


async def variant(name: str, thinking: bool, parts: int) -> tuple[str, dict]:
    results = await asyncio.gather(*(llm(svc._SYSTEM_PROMPT, svc._build_user_prompt(g), thinking=thinking) for g in groups_of(parts)))
    return name, evaluate_current(list(results))


async def cmd_so_sanh() -> None:
    done = await asyncio.gather(
        variant("A. một lời gọi, suy luận mặc định (hiện trạng)", True, 1), variant("B. một lời gọi, tắt suy luận", False, 1),
        variant("C. 4 lời gọi song song, suy luận mặc định", True, 4), variant("D. 4 lời gọi song song, tắt suy luận", False, 4),
    )
    save("ket-qua-01-bon-phuong-an.json", {"sections": len(SECTIONS), "variants": dict(done)})
    for name, summary in done:
        print(f"\n{name}\n  " + json.dumps(summary, ensure_ascii=False))


def deep_metrics(raw: str) -> dict:
    try:
        items = svc._extract_items(json.loads(raw))
    except Exception:
        return {"tasks": 0, "note": "JSON không đọc được"}
    arranged = svc._arrange(svc._parse_proposals(raw, BY_ID, "PROFILE"), [], BY_ID)
    cited = {c.document_section_id for p in arranged for c in p.source_chunks}
    return {
        "tasks": len(arranged), "raw_items": len(items), "covered": f"{len({s.id for s in SECTIONS} & cited)}/{len(SECTIONS)}",
        "dependencies": sum(len(p.prerequisites) for p in arranged), "last_task": arranged[-1].title if arranged else "",
    }


async def cmd_tat_suy_luan() -> None:
    runs = await asyncio.gather(*(llm(svc._SYSTEM_PROMPT, svc._build_user_prompt(SECTIONS), thinking=False) for _ in range(5)))
    rows = []
    for r in runs:
        row = deep_metrics(r["content"]) if r["ok"] else {"error": r["error"]}
        row.update(seconds=round(r["seconds"], 1), tokens_out=r.get("tout", 0))
        rows.append(row)
    save("ket-qua-02-tat-suy-luan-5-lan.json", {"variant": "một lời gọi, tắt suy luận, 5 lần chạy song song", "runs": rows})
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))


# ------------------------------------------------------------------ chia-nhom (phương án đề xuất)
RULES = (
    "Bạn giúp HR soạn task onboarding từ tài liệu nội bộ đã duyệt. Chỉ dùng nội dung được cung cấp. Mặc định mỗi section có hành động "
    "là MỘT task riêng, đặt tên theo hành động; section chỉ là thông tin thì bỏ qua. title ngắn gọn là một hành động. steps là các bước "
    "hành động, mỗi bước một câu đầy đủ, giữ nguyên địa điểm, email, tiêu đề email, hạn chót, liên kết, tên đầu mối. "
    "Nguồn: KHÔNG chép lại câu, chỉ ghi sources = [{section_id, from_line, to_line}] theo số dòng L<n> đã đánh (L0 là tiêu đề), chọn đoạn ngắn nhất đủ làm căn cứ. "
    "needs = các câu điều kiện nguyên văn nếu task chỉ làm được sau việc khác (hoặc rỗng). "
    'Trả JSON {"tasks":[{"title","summary","steps":[...],"done_criteria":[...],"estimated_minutes":số|null,"sources":[...],"task_group":"PROFILE|TRAINING|DEVICE|OFFICE|null","needs":[...],"warnings":[...]}]}.'
)
MERGE_SYSTEM = (
    "Bạn sắp xếp các task onboarding của một tài liệu. Cho danh sách task đánh số kèm điều kiện nguyên văn (needs). "
    'Trả JSON {"order":[các số theo thứ tự nên làm, việc gắn với "cuối ngày" xếp cuối],"prerequisites":{"<số>":[các số phải xong trước]}}. '
    "Chỉ thêm tiên quyết khi tài liệu cho thấy rõ (needs hoặc hiển nhiên như cần có máy/tài khoản trước). Không tạo vòng."
)
LINES: dict[int, list[str]] = {}


def numbered(section) -> str:
    lines = [section.heading or ""] + [ln for ln in section.content.split("\n") if ln.strip()]
    LINES[section.id] = lines
    return f"--- section_id={section.id} ---\n" + "\n".join(f"L{i}: {ln}" for i, ln in enumerate(lines))


def num(value):
    match = re.search(r"\d+", str(value))  # mô hình hay viết "L3" thay vì 3: phải đọc được cả hai
    return int(match.group(0)) if match else None


def quote_of(source: dict) -> str | None:
    lines = LINES.get(num(source.get("section_id")))
    a, b = num(source.get("from_line")), num(source.get("to_line"))
    if lines is None or a is None or b is None:
        return None
    if a > b:
        a, b = b, a
    b = min(b, len(lines) - 1)
    return "\n".join(lines[a : b + 1]) if 0 <= a < len(lines) else None


def tasks_of(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    items = data.get("tasks") if isinstance(data, dict) else data
    out = []
    for t in items if isinstance(items, list) else []:
        if isinstance(t, dict) and t.get("title"):
            t["_quotes"] = [q for q in (quote_of(s) for s in (t.get("sources") or []) if isinstance(s, dict)) if q]
            out.append(t)
    return out


def cited_ids(valid: list[dict]) -> set[int]:
    return {num(s["section_id"]) for t in valid for s in (t.get("sources") or []) if isinstance(s, dict) and quote_of(s)}


async def one_run(parts: int = 4) -> dict:
    started = time.perf_counter()
    results = await asyncio.gather(*(llm(RULES, "\n\n".join(numbered(s) for s in g), thinking=False) for g in groups_of(parts)))
    batch_seconds = time.perf_counter() - started
    valid = [t for r in results if r["ok"] for t in tasks_of(r["content"]) if t["_quotes"]]
    retry_started, extra_tokens = time.perf_counter(), 0
    for _ in range(2):  # bù phủ: các mục chưa có task được hỏi lại riêng (rẻ vì tắt suy luận)
        missing = [s for s in SECTIONS if s.id not in cited_ids(valid)]
        if not missing:
            break
        retry = await asyncio.gather(*(
            llm(RULES + " CÁC MỤC DƯỚI ĐÂY CHƯA CÓ TASK: mỗi mục có hành động cho nhân viên phải có task riêng; chỉ bỏ qua mục thuần thông tin.",
                "\n\n".join(numbered(s) for s in missing[i : i + 4]), thinking=False)
            for i in range(0, len(missing), 4)
        ))
        for r in retry:
            extra_tokens += r.get("tout", 0)
            if r["ok"]:
                valid += [t for t in tasks_of(r["content"]) if t["_quotes"]]
    retry_seconds = time.perf_counter() - retry_started
    listing = "\n".join(f"{i + 1}. {t['title']} | {t.get('summary', '')} | needs: {' / '.join(t.get('needs') or []) or '-'}" for i, t in enumerate(valid))
    merge = await llm(MERGE_SYSTEM, listing, thinking=False)
    deps, permutation, last = 0, False, ""
    if merge["ok"]:
        try:
            data = json.loads(merge["content"])
            deps = sum(len(v) for v in (data.get("prerequisites") or {}).values() if isinstance(v, list))
            order = [int(x) for x in data.get("order", [])]
            permutation = sorted(order) == list(range(1, len(valid) + 1))
            last = valid[order[-1] - 1]["title"] if permutation and order else ""
        except Exception:
            pass
    text = " ".join((t["title"] + " " + (t.get("summary") or "") + " " + " ".join(t.get("steps") or []) + " " + " ".join(t.get("done_criteria") or [])).lower() for t in valid)
    return {
        "tasks": len(valid), "covered": f"{len({s.id for s in SECTIONS} & cited_ids(valid))}/{len(SECTIONS)}",
        "facts": f"{sum(1 for f in FACTS if f.lower() in text)}/{len(FACTS)}", "dependencies": deps, "order_is_permutation": permutation, "last_task": last,
        "seconds_batches": round(batch_seconds, 1), "seconds_coverage_retry": round(retry_seconds, 1), "seconds_merge": round(merge["seconds"], 1),
        "seconds_total": round(time.perf_counter() - started, 1),
        "tokens_out": sum(r.get("tout", 0) for r in results) + extra_tokens + merge.get("tout", 0),
    }


async def cmd_chia_nhom() -> None:
    runs: list[dict] = []
    for _ in range(2):  # 2 đợt x 3 lần chạy song song (mỗi lần chạy tối đa 4 lời gọi cùng lúc)
        runs += await asyncio.gather(*(one_run() for _ in range(3)))
    save("ket-qua-04-chia-nhom-co-bu-phu.json", {"variant": "4 nhóm mục song song, tắt suy luận, trích bằng số dòng, bù phủ, xếp thứ tự (tắt suy luận)", "runs": runs})
    for row in runs:
        print(json.dumps(row, ensure_ascii=False))


async def cmd_mot_loi_goi() -> None:
    runs: list[dict] = []
    for _ in range(2):
        runs += await asyncio.gather(*(one_run(1) for _ in range(3)))
    save("ket-qua-05-mot-loi-goi-so-dong.json", {"variant": "MỘT lời gọi cho cả tài liệu, tắt suy luận, trích bằng số dòng, bù phủ, xếp thứ tự", "runs": runs})
    for row in runs:
        print(json.dumps(row, ensure_ascii=False))


# ------------------------------------------------------------------ stream-do-cham (đo từng pha của MỘT lời gọi)
async def stream_call(system: str, user: str, *, thinking: bool) -> dict:
    """Gọi ở chế độ phát từng đoạn (stream) để thấy lời gọi mất thời gian ở pha nào. Kết quả giống hệt gọi thường (nối các đoạn)."""
    body = {
        "model": MODEL, "stream": True, "stream_options": {"include_usage": True},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }
    if not thinking:
        body["thinking"] = {"type": "disabled"}
    started = time.perf_counter()
    marks: dict[str, float] = {}
    chunks = {"reasoning": 0, "content": 0}
    parts: list[str] = []
    usage: dict = {}
    finish = None
    timeline: list[list[float]] = []  # [giây, số đoạn suy luận, số đoạn nội dung] lấy mẫu mỗi giây
    last_sample = 0.0
    async with httpx.AsyncClient(timeout=httpx.Timeout(400, connect=10)) as client:
        async with client.stream("POST", f"{BASE.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, json=body) as response:
            if response.status_code != 200:
                return {"ok": False, "error": (await response.aread()).decode("utf-8", "replace")[:150]}
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                now = time.perf_counter() - started
                marks.setdefault("first_byte", now)
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                usage = chunk.get("usage") or usage
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    if delta.get("reasoning_content"):
                        marks.setdefault("first_reasoning", now)
                        chunks["reasoning"] += 1
                    if delta.get("content"):
                        marks.setdefault("first_content", now)
                        chunks["content"] += 1
                        parts.append(delta["content"])
                    finish = choice.get("finish_reason") or finish
                if now - last_sample >= 1.0:
                    last_sample = now
                    timeline.append([round(now, 1), chunks["reasoning"], chunks["content"]])
    total = time.perf_counter() - started
    out_tokens = usage.get("completion_tokens", 0)
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    first_content = marks.get("first_content", total)
    reasoning_seconds = max(0.0, first_content - marks.get("first_reasoning", first_content)) if "first_reasoning" in marks else 0.0
    content_seconds = max(0.0, total - first_content)
    content_tokens = out_tokens - reasoning_tokens
    return {
        "ok": True, "content": "".join(parts), "finish_reason": finish,
        "seconds_total": round(total, 1),
        "seconds_to_first_byte": round(marks.get("first_byte", 0), 2),
        "seconds_to_first_reasoning": round(marks["first_reasoning"], 2) if "first_reasoning" in marks else None,
        "seconds_to_first_content": round(first_content, 2),
        "seconds_reasoning_phase": round(reasoning_seconds, 1), "seconds_content_phase": round(content_seconds, 1),
        "tokens_in": usage.get("prompt_tokens", 0), "tokens_out": out_tokens, "tokens_reasoning": reasoning_tokens, "tokens_content": content_tokens,
        "tokens_per_second_reasoning": round(reasoning_tokens / reasoning_seconds) if reasoning_seconds > 1 else None,
        "tokens_per_second_content": round(content_tokens / content_seconds) if content_seconds > 1 else None,
        "cache_hit_tokens": usage.get("prompt_cache_hit_tokens", 0), "chunks": chunks, "timeline": timeline,
    }


def field_shares(raw: str) -> dict:
    """Mỗi trường của task chiếm bao nhiêu phần chữ trong JSON mô hình trả (để biết phần nào làm đầu ra dài)."""
    try:
        items = json.loads(raw).get("tasks", [])
    except Exception:
        return {}
    sizes: dict[str, int] = {}
    for task in items:
        for key, value in task.items():
            sizes[key] = sizes.get(key, 0) + len(json.dumps(value, ensure_ascii=False))
    total = sum(sizes.values()) or 1
    return {key: round(100 * size / total, 1) for key, size in sorted(sizes.items(), key=lambda kv: -kv[1])}


async def cmd_stream() -> None:
    user_current = svc._build_user_prompt(SECTIONS)
    user_numbered = "\n\n".join(numbered(s) for s in SECTIONS)
    runs = await asyncio.gather(
        stream_call(svc._SYSTEM_PROMPT, user_current, thinking=True),
        *(stream_call(RULES, user_numbered, thinking=False) for _ in range(3)),
    )
    labels = ["A. hiện trạng (suy luận bật, lời nhắc hiện tại)"] + [f"F{i}. đề xuất (tắt suy luận, số dòng)" for i in (1, 2, 3)]
    report = []
    for label, run in zip(labels, runs):
        entry = {"label": label, **{k: v for k, v in run.items() if k not in ("content",)}}
        if run.get("ok") and label.startswith("F"):
            entry["field_share_percent"] = field_shares(run["content"])
        report.append(entry)
        print(json.dumps({k: v for k, v in entry.items() if k != "timeline"}, ensure_ascii=False))
    save("ket-qua-06-stream-do-cham.json", {"variant": "đo pha của một lời gọi bằng stream", "runs": report})


COMMANDS = {"so-sanh": cmd_so_sanh, "tat-suy-luan": cmd_tat_suy_luan, "chia-nhom": cmd_chia_nhom, "mot-loi-goi": cmd_mot_loi_goi, "stream-do-cham": cmd_stream}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(__doc__)
    asyncio.run(COMMANDS[sys.argv[1]]())
