# -*- coding: utf-8 -*-
"""Chạy bộ câu hỏi Viga vào một máy chủ (serve_variant.py) và gom: độ chính xác, độ trễ từng câu, token/chi phí từng bước LLM.

- 26 câu tài liệu: lấy NGUYÊN từ docs/.../eval/viga_eval.py (một nguồn duy nhất) cùng cách chấm ✓ / ~ / ✗ của bộ đó.
- 10 câu bổ sung kiểm định tuyến công cụ (lộ trình, ngoài phạm vi, câu tình huống) — xem EXTRA bên dưới.
- Số token, chi phí, độ trễ từng bước đọc từ bảng llm_calls theo X-Request-ID của từng câu (không dựa vào đồng hồ DB).

Chạy: python run_benchmark.py --label A_hien_trang --runs 2 --base http://127.0.0.1:8001
Mật khẩu tài khoản thử đọc từ registry dev và DATABASE_URL từ .env; cả hai không bao giờ được in ra.
"""

import argparse
import asyncio
import json
import re
import statistics
import time
from pathlib import Path

import asyncpg
import httpx

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
EVAL_PY = ROOT / "docs" / "chatbot-vsf" / "plan" / "plan-portal" / "eval" / "viga_eval.py"
USERS = ROOT / "docs" / "chatbot-vsf" / "data" / "registry" / "users.json"
EMAIL = "newhire2@vsf-demo.example"

TASK_TYPES = {"NEXT_STEP", "DAY_PLAN", "INFO", "PREREQUISITE_REQUIRED", "NOT_IN_JOURNEY", "CLARIFY"}
# (id, câu hỏi, loại mong đợi: TASK | ANSWER | DECLINE)
EXTRA = [
    (101, "Hôm nay tôi có việc gì?", "TASK"),
    (102, "Ngày 2 có những việc nào?", "TASK"),
    (103, "Tôi làm được bao nhiêu việc rồi?", "TASK"),
    (104, "Sao tôi chưa làm được việc nhận laptop?", "TASK"),
    (105, "Việc nhận laptop làm thế nào?", "TASK"),
    (106, "Tiếp theo tôi nên làm gì?", "TASK"),
    (107, "Việc nào tôi làm được ngay bây giờ?", "TASK"),
    (108, "tôi đã đăng nhập được outlook nhưng team không vào được thì sao", "ANSWER"),
    (109, "Lương của tôi tháng này bao nhiêu?", "DECLINE"),
    (110, "Hôm nay thời tiết ở Hà Nội thế nào?", "DECLINE"),
]

# Câu NHIỀU Ý trong một lượt (đường tách câu hỏi con của pipeline): (id, câu hỏi, số ý, các ý bắt buộc phải có trong câu trả lời)
MULTI = [
    (201, "Tôi chưa có VNeID thì sao, dùng CMND được không, và tôi không đăng nhập được Teams thì sao?", 3, []),
    (202, "Tôi nhận laptop ở đâu và đăng ký faceid chấm công ở đâu?", 2, ["tầng 12", "tầng 14"]),
    (203, "Bài test cuối khóa phải đạt bao nhiêu phần trăm và đầu mối chương trình Đào tạo Hội nhập là ai?", 2, ["80", "v.thudq@vinsmartfuture.tech"]),
    (204, "Tôi chưa có lý lịch tư pháp thì sao, và T3 chưa trả lời email phê duyệt thì tôi làm sao?", 2, ["giấy hẹn", "nhắc"]),
]

RAW_TASK_DUMP = re.compile(r"##\s*(Vì sao phải làm|Các bước|Điều kiện hoàn thành)")
RAW_MARKDOWN = re.compile(r"\*\*|^\s*\*\s|\\\*|\\_")


def load_cases() -> list[tuple]:
    source = EVAL_PY.read_text(encoding="utf-8")
    start = source.index("CASES = [")
    end = source.index("\n]\n", start) + 3
    scope: dict = {}
    exec(source[start:end], scope)  # noqa: S102 - đọc đúng danh sách câu hỏi của bộ eval có sẵn
    return scope["CASES"]


def password_of(email: str) -> str:
    for user in json.loads(USERS.read_text(encoding="utf-8")):
        if user.get("email") == email:
            return user["password_dev_only"]
    raise SystemExit("không thấy tài khoản")


def database_url() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').replace("+asyncpg", "")
    raise SystemExit("không thấy DATABASE_URL")


def grade_doc_case(expect: str, must: list[str], body: dict) -> dict:
    claims = body.get("claims", [])
    text = " ".join([body.get("message", "")] + [c.get("text") or "" for c in claims] + [c.get("quote") or "" for c in claims]).lower()
    answered = body.get("response_type") == "ANSWER" and any(c["response_type"] == "ANSWER" for c in claims)
    got = "ANSWER" if answered else "NO_BASIS"
    missing = [m for m in must if m.lower() not in text]
    dump = bool(RAW_TASK_DUMP.search(body.get("message", "") + " ".join(c.get("text") or "" for c in claims)))
    raw_md = bool(RAW_MARKDOWN.search(" ".join(c.get("text") or "" for c in claims) + " " + " ".join(c.get("quote") or "" for c in claims)))
    type_ok = expect == "ANY" or got == expect
    verdict = "✓" if type_ok and not missing and not dump and not raw_md else ("~" if type_ok else "✗")
    return {"got": got, "verdict": verdict, "missing": missing}


def grade_extra(expect: str, body: dict) -> dict:
    kind = body.get("response_type")
    if expect == "TASK":
        ok = kind in TASK_TYPES
    elif expect == "ANSWER":
        ok = kind == "ANSWER"
    else:
        ok = kind in {"OUT_OF_SCOPE", "NO_BASIS"}
    return {"got": kind, "verdict": "✓" if ok else "✗", "missing": []}


def grade_multi(parts: int, must: list[str], body: dict) -> dict:
    claims = body.get("claims", [])
    answered = sum(1 for c in claims if c.get("response_type") == "ANSWER")
    text = " ".join([body.get("message", "")] + [c.get("text") or "" for c in claims]).lower()
    missing = [m for m in must if m.lower() not in text]
    verdict = "✓" if answered >= parts and not missing else ("~" if answered >= 1 else "✗")
    return {"got": f"{answered}/{parts} ý", "verdict": verdict, "missing": missing, "claim_count": len(claims), "answered_parts": answered}


def ask(client: httpx.Client, question: str) -> tuple[dict, float, str | None]:
    started = time.perf_counter()
    response = client.post("/api/v1/viga/ask", json={"question": question})
    seconds = time.perf_counter() - started
    body = response.json() if response.status_code == 200 else {"error": response.text[:200], "response_type": "ERROR"}
    return body, round(seconds, 3), response.headers.get("x-request-id")


async def llm_rows(request_ids: list[str]) -> dict[str, list[dict]]:
    connection = await asyncpg.connect(database_url())
    try:
        rows = await connection.fetch(
            """SELECT request_id, operation, kind, latency_ms, prompt_tokens, completion_tokens, reasoning_tokens,
                      cost_usd, ok, attempt FROM llm_calls WHERE request_id = ANY($1::text[]) ORDER BY id""",
            request_ids,
        )
    finally:
        await connection.close()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["request_id"], []).append({k: row[k] for k in row.keys() if k != "request_id"})
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--label", required=True)
    parser.add_argument("--runs", type=int, default=2)
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base, timeout=180)
    login = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": password_of(EMAIL)})
    assert login.status_code == 200, login.status_code
    client.get("/api/v1/portal/me/journey")
    # Một lượt khởi động bỏ qua (tạo kết nối, làm ấm GPU embedding) để các lượt đo không dính độ trễ nguội.
    ask(client, "Hồ sơ cần nộp trong ngày đầu gồm những gì?")

    cases = (
        [("doc", c[0], c[2], c[3], c[4]) for c in load_cases()]
        + [("extra", e[0], e[1], e[2], []) for e in EXTRA]
        + [("multi", m[0], m[1], m[2], m[3]) for m in MULTI]
    )
    results = []
    for run in range(1, args.runs + 1):
        for kind, case_id, question, expect, must in cases:
            body, seconds, request_id = ask(client, question)
            if kind == "doc":
                graded = grade_doc_case(expect, must, body)
            elif kind == "extra":
                graded = grade_extra(expect, body)
            else:
                graded = grade_multi(expect, must, body)
            results.append(
                {
                    "run": run, "id": case_id, "set": kind, "question": question, "expect": expect, "seconds": seconds,
                    "request_id": request_id, "route": body.get("route"), "type": body.get("response_type"), **graded,
                }
            )
            print(f"run{run} #{case_id} {graded['verdict']} {body.get('response_type')} {seconds}s", flush=True)

    grouped = asyncio.run(llm_rows([r["request_id"] for r in results if r["request_id"]]))
    for result in results:
        result["llm_calls"] = grouped.get(result["request_id"], [])

    out = HERE.parent / "ket-qua" / f"{args.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"label": args.label, "runs": args.runs, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    seconds = [r["seconds"] for r in results]
    ok = sum(r["verdict"] == "✓" for r in results)
    print(f"{args.label}: {ok}/{len(results)} ✓ · trung vị {statistics.median(seconds):.2f}s → {out.name}")


main()
