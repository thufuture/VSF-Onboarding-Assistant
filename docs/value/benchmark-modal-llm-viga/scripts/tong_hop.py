# -*- coding: utf-8 -*-
"""Tổng hợp ket-qua/*.json thành các bảng Markdown (in ra màn hình và lưu bang-so-lieu.md). Mọi con số đều tính từ dữ liệu thô."""

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ORDER = ["A_hien_trang", "B_tat_route_rewrite", "C_tat_ca"]
NAMES = {
    "A_hien_trang": "A. Hiện trạng (thinking bật ở cả 3 bước)",
    "B_tat_route_rewrite": "B. Tắt thinking ở route + rewrite",
    "C_tat_ca": "C. Tắt thinking ở cả route, rewrite, answer",
}
OPS = ["viga.route", "chat.rewrite", "chat.embed", "chat.answer"]


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, round(q * (len(ordered) - 1)))
    return ordered[index]


def load() -> dict[str, dict]:
    data = {}
    for path in sorted((BASE / "ket-qua").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        data[payload["label"]] = payload
    return data


def table(rows: list[list[str]], header: list[str]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def main() -> None:
    data = load()
    labels = [label for label in ORDER if label in data]
    out: list[str] = []

    # 1. Độ chính xác
    rows = []
    for label in labels:
        results = data[label]["results"]
        row = [NAMES[label]]
        for kind in ("doc", "extra", "multi"):
            subset = [r for r in results if r["set"] == kind]
            ok = sum(r["verdict"] == "✓" for r in subset)
            part = sum(r["verdict"] == "~" for r in subset)
            row.append(f"{ok}/{len(subset)} ✓ · {part} ~ · {len(subset) - ok - part} ✗")
        all_ok = sum(r["verdict"] == "✓" for r in results)
        row.append(f"**{all_ok}/{len(results)}** ({100 * all_ok / len(results):.1f}%)")
        rows.append(row)
    out += ["### Độ chính xác (cộng cả các lượt chạy)", table(rows, ["Phương án", "26 câu tài liệu", "10 câu định tuyến", "4 câu nhiều ý", "Tổng ✓"])]

    # 2. Độ trễ đầu-cuối
    rows = []
    for label in labels:
        seconds = [r["seconds"] for r in data[label]["results"]]
        rows.append([NAMES[label], f"{statistics.median(seconds):.2f}", f"{statistics.mean(seconds):.2f}", f"{pct(seconds, 0.95):.2f}", f"{max(seconds):.2f}", str(len(seconds))])
    out += ["", "### Độ trễ một câu hỏi (giây, đo ở phía người dùng)", table(rows, ["Phương án", "Trung vị", "Trung bình", "p95", "Lớn nhất", "Số lượt"])]

    # 3. Theo bước LLM
    for metric, title, fmt in (
        ("latency_ms", "Độ trễ trung bình mỗi lần gọi (giây)", lambda v: f"{v / 1000:.2f}"),
        ("completion_tokens", "Token đầu ra trung bình mỗi lần gọi (gồm cả suy luận ẩn)", lambda v: f"{v:.0f}"),
        ("reasoning_tokens", "Trong đó token suy luận ẩn", lambda v: f"{v:.0f}"),
        ("prompt_tokens", "Token đầu vào trung bình mỗi lần gọi", lambda v: f"{v:.0f}"),
    ):
        rows = []
        for label in labels:
            calls = [c for r in data[label]["results"] for c in r["llm_calls"]]
            row = [NAMES[label]]
            for op in OPS:
                values = [c[metric] for c in calls if c["operation"] == op]
                row.append(fmt(statistics.mean(values)) if values else "–")
            rows.append(row)
        out += ["", f"### {title}", table(rows, ["Phương án", *OPS])]

    # 4. Chi phí
    rows = []
    for label in labels:
        results = data[label]["results"]
        costs = [sum(c["cost_usd"] for c in r["llm_calls"]) for r in results]
        by_op = {op: sum(c["cost_usd"] for r in results for c in r["llm_calls"] if c["operation"] == op) / len(results) for op in OPS}
        rows.append([NAMES[label], f"{statistics.mean(costs) * 1000:.3f}", *(f"{by_op[op] * 1000:.3f}" for op in OPS), f"{statistics.mean(costs) * 1000:.2f}"])
    out += [
        "",
        "### Chi phí ước tính mỗi câu hỏi (mili-USD; cột cuối: USD cho 1.000 câu)",
        table(rows, ["Phương án", "Tổng/câu", *OPS, "USD/1.000 câu"]),
    ]

    # 5. So với hiện trạng
    base = data.get("A_hien_trang")
    if base:
        rows = []
        key = lambda r: (r["run"], r["id"])
        base_by = {key(r): r for r in base["results"]}
        for label in labels[1:]:
            other = data[label]["results"]
            flips = [(base_by[key(r)], r) for r in other if key(r) in base_by and base_by[key(r)]["verdict"] != r["verdict"]]
            worse = [pair for pair in flips if "✓~✗".index(pair[1]["verdict"]) > "✓~✗".index(pair[0]["verdict"])]
            better = len(flips) - len(worse)
            rows.append([NAMES[label], str(len(flips)), str(len(worse)), str(better)])
        out += ["", "### Số câu đổi kết quả so với hiện trạng (cùng câu, cùng lượt)", table(rows, ["Phương án", "Đổi kết quả", "Tệ đi", "Tốt lên"])]

    text = "\n".join(out) + "\n"
    (BASE / "bang-so-lieu.md").write_text(text, encoding="utf-8")
    sys.stdout.buffer.write(text.encode("utf-8"))


main()
