# -*- coding: utf-8 -*-
"""Sinh các bảng của báo cáo tối ưu độ trễ TỪ FILE KẾT QUẢ THÔ (không gõ tay số nào): `python tong_hop_bang.py > bang.md`.

File thô: ket-qua-14-* (đường nhanh, mã cuối), ket-qua-15-* (đường cũ, cùng đợt), ket-qua-11-* (chạy thật qua API và job).
Thư mục dot-do-truoc-khi-sua-loi/ giữ các đợt đo trước khi sửa hai lỗi tìm ra nhờ chính phép đo (xem báo cáo, mục 8).
"""

import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))


def spread(values: list, digits: int = 1) -> str:
    values = [v for v in values if v is not None]
    if not values:
        return "-"
    return f"{min(values):.{digits}f} / {st.median(values):.{digits}f} / {max(values):.{digits}f}"


def ints(values: list) -> str:
    return spread(values, 0)


def facts_range(runs: list[dict]) -> str:
    got = [int(r["facts"].split("/")[0]) for r in runs if r["facts"] != "n/a"]
    if not got:
        return "không áp dụng"
    total = next(int(r["facts"].split("/")[1]) for r in runs if r["facts"] != "n/a")
    return f"{min(got)}–{max(got)}/{total}"


def row(label: str, data: dict) -> str:
    all_runs = data["runs"]
    runs = [r for r in all_runs if not r.get("error")]
    errors = len(all_runs) - len(runs)
    full = sum(1 for r in runs if r["covered"].split("/")[0] == r["covered"].split("/")[1])
    eod = [r["end_of_day_after_others"] for r in runs if r.get("end_of_day_after_others") is not None]
    eod_text = f"{sum(1 for v in eod if v)}/{len(eod)}" if eod else "không áp dụng"
    return (
        f"| {label} | {len(runs)}{f' (+{errors} lỗi)' if errors else ''} | {spread([r['seconds'] for r in runs])} | "
        f"{ints([r['tasks'] for r in runs])} | {full}/{len(runs)} | {facts_range(runs)} | "
        f"{sum(1 for r in runs if r['quotes_all_verbatim'])}/{len(runs)} | {eod_text} | "
        f"{ints([r['dependencies'] for r in runs])} | {sum(1 for r in runs if r['empty_steps'])}/{len(runs)} | "
        f"{ints([r['tokens_out'] for r in runs])} | {spread([r['cost_usd'] for r in runs], 4)} |"
    )


HEAD = (
    "| Cách chạy | Số lần | Giây (nhỏ nhất / giữa / lớn nhất) | Số task | Lần phủ đủ mọi mục | Chi tiết thật giữ được | "
    "Quote nguyên văn | Việc cuối ngày đứng sau | Tiên quyết | Lần có task thiếu bước | Token ra | USD mỗi lần |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|"
)

print('### Bảng 1. Tài liệu "Hướng dẫn ngày 1" (16 mục)\n')
print(HEAD)
print(row("Cũ (legacy), suy luận bật", load("ket-qua-15-ngay1-legacy")))
print(row("Nhanh (fast), chạy lần lượt", load("ket-qua-14-ngay1-fast")))
print(row("Nhanh, 3 người bấm cùng lúc", load("ket-qua-14-ngay1-fast-3-nguoi-cung-luc")))

print('\n### Bảng 2. Tài liệu "Các trường hợp ngoại lệ" (22 mục, phần lớn là hỏi đáp thông tin)\n')
print(HEAD)
legacy2 = load("ket-qua-15-ngoai-le-legacy")
fast2 = load("ket-qua-14-ngoai-le-fast")
print(row("Cũ (legacy), suy luận bật", legacy2))
print(row("Nhanh (fast), chạy lần lượt", fast2))
print(
    "\nSố mục bị coi là chỉ có thông tin, theo từng lần: nhanh "
    + ", ".join(str(r["skipped_sections"]) for r in fast2["runs"])
    + "; đường cũ báo \"chưa có task\" "
    + ", ".join(str(r["uncovered_reported"]) for r in legacy2["runs"])
    + "."
)

print('\n### Bảng 3. File docx không tiêu đề "Hướng dẫn ngày 1" (687 từ, ingest suy ra 3 mục có tiêu đề)\n')
print(HEAD)
print(row("Cũ (legacy), suy luận bật", load("ket-qua-15-docx-khong-header-legacy")))
print(row("Nhanh (fast), chạy lần lượt", load("ket-qua-14-docx-khong-header-fast")))

print("\n### Bảng 4. Thời gian từng bước của đường nhanh (giây, nhỏ nhất / giữa / lớn nhất)\n")
print("| Tài liệu | Soạn (draft) | Xếp thứ tự (order) | Bù phủ (cover) | Tổng |\n|---|---|---|---|---|")
for label, name in (
    ("Hướng dẫn ngày 1", "ket-qua-14-ngay1-fast"),
    ("Các trường hợp ngoại lệ", "ket-qua-14-ngoai-le-fast"),
    ("docx không tiêu đề", "ket-qua-14-docx-khong-header-fast"),
):
    runs = [r for r in load(name)["runs"] if not r.get("error")]
    cover = [r["step_seconds"]["cover"] for r in runs if "cover" in r["step_seconds"]]
    cover_text = f"{spread(cover)} (có ở {len(cover)}/{len(runs)} lần)" if cover else "không lần nào cần"
    print(
        f"| {label} | {spread([r['step_seconds']['draft'] for r in runs])} | {spread([r['step_seconds'].get('order') for r in runs])} | "
        f"{cover_text} | {spread([r['seconds'] for r in runs])} |"
    )

e2e = load("ket-qua-11-job-that-tren-db")
print("\n### Bảng 5. Chạy thật end-to-end (API, job, DeepSeek thật, đọc tiến độ mỗi 0,5 giây)\n")
print("| Kịch bản | Job | Giây chạy (worker đo) | Mẫu tiến độ | Tài liệu | Số task | Mục bị bỏ qua (thông tin) | Nguồn thứ tự |\n|---|---|---|---|---|---|---|---|")
for name, sc in e2e["scenarios"].items():
    docs = sc["documents"]
    print(
        f"| {name} | {sc['job_id']} | {sc['elapsed_seconds']} | {len(sc['timeline'])} | {len(docs)} | "
        f"{' + '.join(str(d['tasks']) for d in docs)} | {' + '.join(str(d['skipped_info']) for d in docs)} | "
        f"{', '.join(d['metrics']['order_source'] for d in docs)} |"
    )

print("\n### Bảng 6. Các pha của từng lời gọi LLM trong `llm_calls` (mili-giây)\n")
print("| Lời gọi | Chờ chỗ | Byte đầu | Chữ đầu | Suy luận | Viết JSON | Tổng | Token vào (cache) | Token ra | Suy luận (token) | Kết thúc |\n|---|---|---|---|---|---|---|---|---|---|---|")
for c in e2e["llm_calls"]:
    kind = "soạn" if c["completion_tokens"] > 1000 else "xếp thứ tự"
    print(
        f"| #{c['id']} ({kind}) | {c['queue_wait_ms']} | {c['first_byte_ms']} | {c['first_token_ms']} | {c['reasoning_ms']} | {c['content_ms']} | "
        f"{c['latency_ms']} | {c['prompt_tokens']} ({c['cached_input_tokens']}) | {c['completion_tokens']} | {c['reasoning_tokens']} | {c['finish_reason']} |"
    )

print("\n### Bảng 7. Mốc thời gian của thanh tiến độ (một tài liệu, đọc qua API)\n")
sc = e2e["scenarios"]["mot-tai-lieu-1"]
print("| Giây | Trạng thái | % | read | draft | verify | cover | order | save |\n|---|---|---|---|---|---|---|---|---|")
last = None
for r in sc["timeline"]:
    key = (r["percent"] // 10, tuple(r["steps"].items()))
    if key == last:
        continue
    last = key
    s = r["steps"]
    print(f"| {r['t']} | {r['status']} | {r['percent']} | " + " | ".join(s.get(k, "-") for k in ("read", "draft", "verify", "cover", "order", "save")) + " |")

print("\n### Tổng hợp chung (mọi lượt đo cuối)\n")
fast_runs = [
    r
    for name in ("ket-qua-14-ngay1-fast", "ket-qua-14-ngay1-fast-3-nguoi-cung-luc", "ket-qua-14-ngoai-le-fast", "ket-qua-14-docx-khong-header-fast")
    for r in load(name)["runs"]
]
legacy_runs = [
    r for name in ("ket-qua-15-ngay1-legacy", "ket-qua-15-ngoai-le-legacy", "ket-qua-15-docx-khong-header-legacy") for r in load(name)["runs"]
]


def summary(label: str, runs: list[dict]) -> str:
    ok = [r for r in runs if not r.get("error")]
    eod = [r["end_of_day_after_others"] for r in ok if r.get("end_of_day_after_others") is not None]
    return (
        f"| {label} | {len(runs)} | {len(runs) - len(ok)} | {spread([r['seconds'] for r in ok])} | "
        f"{sum(1 for r in ok if r['quotes_all_verbatim'])}/{len(ok)} | {sum(1 for r in ok if r['dependencies_point_backwards_only'])}/{len(ok)} | "
        f"{sum(1 for v in eod if v)}/{len(eod)} | {sum(r['duplicate_titles'] for r in ok)} | "
        f"{sum(1 for r in ok if r['order_source'] == 'document')} | {sum(r['tokens_reasoning'] for r in ok)} | {sum(r['retries'] for r in ok)} | "
        f"{sum(r['cost_usd'] for r in ok):.3f} |"
    )


print(
    "| Đường | Lượt chạy | Lỗi | Giây (nhỏ nhất / giữa / lớn nhất) | Quote nguyên văn | Tiên quyết chỉ trỏ về trước | Việc cuối ngày đứng sau | "
    "Tên task trùng | Phải dùng thứ tự dự phòng | Token suy luận | Lần thử lại | Tổng USD |\n|---|---|---|---|---|---|---|---|---|---|---|---|"
)
print(summary("Cũ (legacy)", legacy_runs))
print(summary("Nhanh (fast)", fast_runs))
