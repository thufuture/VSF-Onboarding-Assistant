"""Tổng hợp và so sánh các cấu hình benchmark Viga: trung bình ± độ lệch giữa các lượt, khoảng tin cậy 95%, kiểm định cặp.

Đọc ket-qua/<nhãn>/điểm_lượt_*.jsonl (do score_benchmark.py tạo). Ghi ket-qua/summary.json và ket-qua/tables.md.
Theo checklist slide ngày 14: >= 3 lượt, mean ± std/CI, kiểm định t cặp p < 0,05, effect size, tách theo nhóm.
Cần scipy: dùng venv có scipy (xem README).

Chạy: PYTHONIOENCODING=utf-8 python docs/value/optimize-chatviga/scripts/compare_configs.py --base R0_full --test R1_full [--safety-base R0_safety --safety-test R1_safety]
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

DIR = Path(__file__).resolve().parents[1] / "ket-qua"
JUDGES = ("deepseek", "openai", "haiku", "groq")


def load(label: str) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(p for p in (DIR / label).glob("điểm_lượt_*.jsonl") if "lần_đầu" not in p.name):  # tệp lần đầu chỉ để báo số lỗi, không gộp
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return rows


def judge_values(row: dict, key: str) -> list[float]:
    values = []
    for judge in JUDGES:
        out = row.get(f"giám_khảo_{judge}")
        if isinstance(out, dict) and isinstance(out.get(key), (int, float)):
            values.append(float(out[key]))
    return values


def faithfulness(row: dict) -> list[float]:
    values = []
    for judge in JUDGES:
        out = row.get(f"giám_khảo_{judge}")
        if isinstance(out, dict) and isinstance(out.get("claims"), list) and out["claims"]:
            flags = [bool(c.get("duoc_ngu_canh_do")) for c in out["claims"] if isinstance(c, dict)]
            if flags:
                values.append(sum(flags) / len(flags))
    return values


def metric(row: dict, name: str) -> float | None:
    if name == "judge_dung":
        v = judge_values(row, "dung")
        return statistics.mean(v) if v else None
    for key in ("du_y", "lien_quan", "mach_lac"):
        if name == f"judge_{key}":
            v = judge_values(row, key)
            return statistics.mean(v) if v else None
    if name == "faithfulness":
        v = faithfulness(row)
        return statistics.mean(v) if v else None
    if name == "đúng_và_có_căn_cứ":
        d, f = metric(row, "judge_dung"), metric(row, "faithfulness")
        if d is None or f is None:
            return None
        return 1.0 if d >= 4 and f >= 0.85 and not row.get("lỗi") else 0.0
    value = row.get(name)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value) if isinstance(value, (int, float)) else None


def per_run(rows: list[dict], name: str) -> list[float]:
    by_run: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        v = metric(row, name)
        if v is not None:
            by_run[row["lượt"]].append(v)
    return [statistics.mean(vs) for _, vs in sorted(by_run.items()) if vs]


def mean_std(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n_lượt": 0}
    out: dict[str, Any] = {"n_lượt": len(values), "trung_bình": statistics.mean(values), "std": statistics.stdev(values) if len(values) > 1 else 0.0}
    if len(values) > 1:
        t = stats.t.ppf(0.975, len(values) - 1)
        half = t * out["std"] / math.sqrt(len(values))
        out["ci95"] = [out["trung_bình"] - half, out["trung_bình"] + half]
    return out


def fmt(entry: dict, digits: int = 3, pct: bool = False) -> str:
    if not entry.get("n_lượt"):
        return "n/a"
    scale = 100 if pct else 1
    suffix = "%" if pct else ""
    base = f"{entry['trung_bình'] * scale:.{digits}f}{suffix}"
    return f"{base} ± {entry['std'] * scale:.{digits}f}" if entry["n_lượt"] > 1 else base


def percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    arr = np.array(values)
    return {"n": len(values), "p50": float(np.percentile(arr, 50)), "p95": float(np.percentile(arr, 95)), "p99": float(np.percentile(arr, 99)), "trung_bình": float(arr.mean())}


def paired(base_rows: list[dict], test_rows: list[dict], name: str) -> dict[str, Any] | None:
    """Kiểm định cặp trên trung bình theo từng câu (qua các lượt)."""
    def per_item(rows: list[dict]) -> dict[str, float]:
        bucket: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            v = metric(row, name)
            if v is not None:
                bucket[row["id"]].append(v)
        return {k: statistics.mean(v) for k, v in bucket.items()}

    a, b = per_item(base_rows), per_item(test_rows)
    ids = sorted(set(a) & set(b))
    if len(ids) < 5:
        return None
    x, y = np.array([a[i] for i in ids]), np.array([b[i] for i in ids])
    diff = y - x
    out: dict[str, Any] = {"n_câu": len(ids), "base": float(x.mean()), "test": float(y.mean()), "delta": float(diff.mean())}
    sd = float(diff.std(ddof=1))
    half = float(stats.t.ppf(0.975, len(ids) - 1) * sd / math.sqrt(len(ids)))
    out["delta_ci95"] = [out["delta"] - half, out["delta"] + half]
    out["cohen_dz"] = float(diff.mean() / sd) if sd > 0 else 0.0
    if sd > 0:
        out["p_t_cặp"] = float(stats.ttest_rel(y, x).pvalue)
        try:
            out["p_wilcoxon"] = float(stats.wilcoxon(y, x).pvalue) if np.any(diff != 0) else 1.0
        except ValueError:
            out["p_wilcoxon"] = None
    else:
        out["p_t_cặp"] = 1.0 if out["delta"] == 0 else 0.0
    return out


def agreement(rows: list[dict]) -> dict[str, Any]:
    pairs = []
    for row in rows:
        a, b = judge_values({**row, "giám_khảo_openai": None}, "dung"), None
        da = (row.get("giám_khảo_deepseek") or {}).get("dung")
        ob = (row.get("giám_khảo_openai") or {}).get("dung")
        if isinstance(da, (int, float)) and isinstance(ob, (int, float)):
            pairs.append((float(da), float(ob)))
        del a, b
    if len(pairs) < 5:
        return {"n": len(pairs)}
    x, y = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    rho = float(stats.spearmanr(x, y).statistic) if x.std() > 0 and y.std() > 0 else float("nan")
    hx, hy = x >= 4, y >= 4
    po = float((hx == hy).mean())
    pe = float(hx.mean() * hy.mean() + (1 - hx.mean()) * (1 - hy.mean()))
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return {"n": len(pairs), "spearman": rho, "cohen_kappa_nhị_phân_(>=4)": kappa, "đồng_thuận_thô": po, "chênh_>=2_điểm": float((abs(x - y) >= 2).mean())}


DOC_METRICS = [
    ("ctx_recall", "Context Recall", True), ("ctx_precision", "Context Precision", True), ("hit1", "Hit@1", True), ("hit3", "Hit@3", True), ("hit5", "Hit@5", True),
    ("mrr", "MRR", False), ("độ_phủ_ý_bắt_buộc", "Phủ ý bắt buộc", True), ("faithfulness", "Faithfulness (giám khảo)", True), ("judge_dung", "Đúng 1-5 (giám khảo)", False),
    ("judge_du_y", "Đủ ý 1-5", False), ("judge_lien_quan", "Liên quan 1-5 (Answer Relevancy)", False), ("judge_mach_lac", "Mạch lạc 1-5", False),
    ("đúng_và_có_căn_cứ", "North Star: đúng và có căn cứ", True), ("loại_đúng", "Đúng loại phản hồi", True), ("lỗi", "Tỉ lệ lỗi", True),
    ("số_mục_cung_cấp", "Số mục đưa vào LLM", False), ("token_ngữ_cảnh", "Token ngữ cảnh", False), ("token_vào", "Token vào (cả câu)", False), ("chi_phí_usd", "Chi phí LLM mỗi câu (USD)", False),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="R0_full")
    parser.add_argument("--test", default="R1_full")
    parser.add_argument("--safety-base", default="R0_safety")
    parser.add_argument("--safety-test", default="R1_safety")
    args = parser.parse_args()
    base, test = load(args.base), load(args.test)
    first_errors: dict[str, Any] = {}
    for label in (args.base, args.test, args.safety_base, args.safety_test):
        path = DIR / label / "điểm_lượt_1_lần_đầu.jsonl"
        if path.exists():
            first = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            first_errors[label] = {"số_câu": len(first), "lỗi_lần_đầu": sum(1 for r in first if r.get("lỗi"))}
    summary: dict[str, Any] = {"lỗi_hạ_tầng_lần_đầu": first_errors, "nhãn": {"base": args.base, "test": args.test}, "số_lượt": {"base": len({r['lượt'] for r in base}), "test": len({r['lượt'] for r in test})}}
    lines: list[str] = []

    def doc_rows(rows: list[dict]) -> list[dict]:
        return [r for r in rows if r.get("route_kỳ_vọng") == "document" and r.get("loại_kỳ_vọng") == "ANSWER"]

    # ---- Luồng C: tài liệu có đáp án
    lines += ["## Luồng C — tìm kiếm tài liệu (câu có đáp án)", "", f"| Chỉ số | {args.base} | {args.test} | Δ (test − base) | 95% CI của Δ | p (t cặp) | p (Wilcoxon) | Cohen d |", "|---|---|---|---|---|---|---|---|"]
    summary["luồng_C"] = {}
    for key, label, pct in DOC_METRICS:
        a_runs, b_runs = per_run(doc_rows(base), key), per_run(doc_rows(test), key)
        cmp = paired(doc_rows(base), doc_rows(test), key)
        summary["luồng_C"][key] = {"base": mean_std(a_runs), "test": mean_std(b_runs), "so_sánh": cmp}
        if cmp:
            scale = 100 if pct else 1
            unit = " điểm %" if pct else ""
            lines.append(f"| {label} | {fmt(mean_std(a_runs), 3 if not pct else 1, pct)} | {fmt(mean_std(b_runs), 3 if not pct else 1, pct)} | {cmp['delta'] * scale:+.3f}{unit} | [{cmp['delta_ci95'][0] * scale:+.3f}, {cmp['delta_ci95'][1] * scale:+.3f}] | {cmp.get('p_t_cặp', float('nan')):.4f} | {cmp.get('p_wilcoxon') if cmp.get('p_wilcoxon') is not None else float('nan'):.4f} | {cmp['cohen_dz']:+.2f} |")
        else:
            lines.append(f"| {label} | {fmt(mean_std(a_runs), 3 if not pct else 1, pct)} | {fmt(mean_std(b_runs), 3 if not pct else 1, pct)} | n/a | | | | |")
    lines.append("")

    # ---- độ trễ theo luồng
    lines += ["## Độ trễ và chi phí theo luồng (gộp mọi lượt, giây)", "", "| Cấu hình | Luồng thực | n | P50 | P95 | P99 | Trung bình | Chi phí LLM/câu (USD) |", "|---|---|---|---|---|---|---|---|"]
    summary["độ_trễ"] = {}
    for label, rows in ((args.base, base), (args.test, test)):
        by_route: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            by_route[row["route_thực"]].append(row)
        by_route["(tất cả — gộp, KHÔNG nên dùng làm số chính)"] = rows
        for route, items in sorted(by_route.items()):
            p = percentiles([r["tổng_giây"] for r in items])
            cost = statistics.mean(r["chi_phí_usd"] for r in items)
            summary["độ_trễ"].setdefault(label, {})[route] = {**p, "chi_phí_usd_mỗi_câu": cost}
            lines.append(f"| {label} | {route} | {p['n']} | {p['p50']:.2f} | {p['p95']:.2f} | {p['p99']:.2f} | {p['trung_bình']:.2f} | {cost:.5f} |")
    lines.append("")
    lines += ["### Thời gian từng bước, luồng tài liệu có đáp án (giây, trung bình)", "", f"| Bước | {args.base} | {args.test} |", "|---|---|---|"]
    for step in ("router", "rewrite", "embed", "truy_hồi", "giây_rerank", "trả_lời", "kiểm_trích_dẫn"):
        key = step if step == "giây_rerank" else f"giây_{step}"
        a = [r[key] for r in doc_rows(base) if key in r]
        b = [r[key] for r in doc_rows(test) if key in r]
        if a or b:
            lines.append(f"| {step} | {statistics.mean(a):.3f} | {statistics.mean(b):.3f} |")
    lines.append("")

    # ---- Luồng A: định tuyến
    lines += ["## Luồng A — định tuyến ý định", "", f"| Nhóm (route kỳ vọng) | n/lượt | {args.base} đúng | {args.test} đúng |", "|---|---|---|---|"]
    summary["luồng_A"] = {}
    for route in ("document", "tool", "out_of_scope", "personal", "injection", "smalltalk"):
        a = [r for r in base if r.get("route_kỳ_vọng") == route]
        b = [r for r in test if r.get("route_kỳ_vọng") == route]
        if a:
            sa, sb = mean_std(per_run(a, "route_đúng")), mean_std(per_run(b, "route_đúng"))
            summary["luồng_A"][route] = {"base": sa, "test": sb, "n": len({r['id'] for r in a})}
            lines.append(f"| {route} | {len({r['id'] for r in a})} | {fmt(sa, 1, True)} | {fmt(sb, 1, True)} |")
    confusion: dict[tuple[str, str], int] = defaultdict(int)
    for r in base:
        if r.get("route_kỳ_vọng"):
            confusion[(r["route_kỳ_vọng"], r["route_thực"])] += 1
    summary["luồng_A"]["ma_trận_nhầm_lẫn_base"] = {f"{k[0]} -> {k[1]}": v for k, v in confusion.items()}
    lines += ["", "Ma trận nhầm lẫn của " + args.base + " (kỳ vọng → thực tế, tổng các lượt):", ""] + [f"- `{k[0]}` → `{k[1]}`: {v}" for k, v in sorted(confusion.items())] + [""]

    # ---- Luồng B: công cụ
    lines += ["## Luồng B — công cụ hành trình", "", f"| Chỉ số | {args.base} | {args.test} |", "|---|---|---|"]
    tool_single = lambda rows: [r for r in rows if r.get("route_kỳ_vọng") == "tool" and r.get("loại_câu") == "đơn"]  # noqa: E731
    tool_multi = lambda rows: [r for r in rows if r.get("route_kỳ_vọng") == "tool" and r.get("loại_câu") == "kép"]  # noqa: E731
    for key, label, subset in (("công_cụ_đúng", "Chọn đúng công cụ (câu đơn)", tool_single), ("tham_số_ngày_đúng", "Đúng tham số ngày (get_day_plan)", tool_single), ("độ_phủ_công_cụ", "Độ phủ các công cụ cần gọi (câu kép)", tool_multi)):
        sa, sb = mean_std(per_run(subset(base), key)), mean_std(per_run(subset(test), key))
        summary.setdefault("luồng_B", {})[key] = {"base": sa, "test": sb}
        lines.append(f"| {label} | {fmt(sa, 1, True)} | {fmt(sb, 1, True)} |")
    lines.append("")

    # ---- theo nhóm câu
    lines += ["## Theo nhóm câu hỏi (đúng loại phản hồi, lỗi, độ phủ ý)", "", f"| Nhóm | n | {args.base} đúng loại | {args.test} đúng loại | {args.base} lỗi | {args.test} lỗi |", "|---|---|---|---|---|---|"]
    for group in sorted({r["nhóm"] for r in base if r.get("nhóm")}):
        a = [r for r in base if r.get("nhóm") == group]
        b = [r for r in test if r.get("nhóm") == group]
        lines.append(f"| {group} | {len({r['id'] for r in a})} | {fmt(mean_std(per_run(a, 'loại_đúng')), 1, True)} | {fmt(mean_std(per_run(b, 'loại_đúng')), 1, True)} | {fmt(mean_std(per_run(a, 'lỗi')), 1, True)} | {fmt(mean_std(per_run(b, 'lỗi')), 1, True)} |")
    lines.append("")

    # ---- đồng thuận giám khảo
    summary["đồng_thuận_giám_khảo"] = agreement(doc_rows(base) + doc_rows(test))
    lines += ["## Đồng thuận giữa hai giám khảo (DeepSeek và gpt-5-mini, điểm 'Đúng')", "", "```", json.dumps(summary["đồng_thuận_giám_khảo"], ensure_ascii=False, indent=1), "```", ""]

    # ---- an toàn
    sb_rows, st_rows = load(args.safety_base), load(args.safety_test)
    if sb_rows:
        lines += ["## Bộ an toàn và độ bền", "", f"| Bộ | n | {args.safety_base}: an toàn cơ học | {args.safety_test}: an toàn cơ học | {args.safety_base}: lỗi | {args.safety_test}: lỗi | {args.safety_base}: làm theo lệnh độc (giám khảo) |", "|---|---|---|---|---|---|---|"]
        summary["an_toàn"] = {}
        for suite in sorted({r["bộ"] for r in sb_rows}):
            a = [r for r in sb_rows if r["bộ"] == suite]
            b = [r for r in st_rows if r["bộ"] == suite]
            followed = [1.0 if any(isinstance(r.get(f"giám_khảo_{j}"), dict) and r[f"giám_khảo_{j}"].get("lam_theo_lenh_doc") for j in JUDGES) else 0.0 for r in a if any(isinstance(r.get(f"giám_khảo_{j}"), dict) for j in JUDGES)]
            summary["an_toàn"][suite] = {"n": len({r['id'] for r in a}), "an_toàn_cơ_học_base": mean_std(per_run(a, "an_toàn_cơ_học")), "an_toàn_cơ_học_test": mean_std(per_run(b, "an_toàn_cơ_học")), "làm_theo_lệnh_độc_theo_giám_khảo": (sum(followed) / len(followed)) if followed else None}
            lines.append(f"| {suite} | {len({r['id'] for r in a})} | {fmt(mean_std(per_run(a, 'an_toàn_cơ_học')), 1, True)} | {fmt(mean_std(per_run(b, 'an_toàn_cơ_học')), 1, True)} | {fmt(mean_std(per_run(a, 'lỗi')), 1, True)} | {fmt(mean_std(per_run(b, 'lỗi')), 1, True)} | {('%.1f%%' % (100 * sum(followed) / len(followed))) if followed else 'n/a'} |")
        # thiên lệch: cặp
        pairs: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
        for r in sb_rows:
            if r.get("mã_cặp"):
                pairs[(r["mã_cặp"], r["lượt"])][r["vế"]] = r
        sims, same = [], []
        for (_, _), sides in pairs.items():
            if "A" in sides and "B" in sides:
                wa, wb = set(sides["A"].get("văn_bản_trả_lời", "").lower().split()), set(sides["B"].get("văn_bản_trả_lời", "").lower().split())
                sims.append(len(wa & wb) / len(wa | wb) if wa | wb else 1.0)
                same.append(sides["A"]["loại_thực"] == sides["B"]["loại_thực"])
        summary["thiên_lệch"] = {"số_cặp_x_lượt": len(sims), "cùng_loại_phản_hồi": (sum(same) / len(same)) if same else None, "độ_giống_từ_trung_bình": statistics.mean(sims) if sims else None}
        lines += ["", f"Thiên lệch (3 cặp × {len({r['lượt'] for r in sb_rows})} lượt): cùng loại phản hồi {100 * summary['thiên_lệch']['cùng_loại_phản_hồi']:.0f}% ; độ giống từ trung bình giữa hai vế {summary['thiên_lệch']['độ_giống_từ_trung_bình']:.2f} (Jaccard).", ""] if sims else [""]
    (DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (DIR / "tables.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
