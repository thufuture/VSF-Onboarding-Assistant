"""Tổng hợp ma trận 2 × 3 của benchmark cuối (tập kiểm 50 câu): RRF tối ưu và RRF + rerank tối ưu × suy luận bật / tắt / thích ứng.

Đọc ket-qua/F_<nhánh>_<chế độ>/điểm_lượt_1.jsonl (do score_benchmark.py tạo). Ghi ket-qua/cuoi/tong_hop.json và tong_hop.md.
Cần numpy và scipy (dùng venv-ci trong thư mục tạm).

Chạy: PYTHONIOENCODING=utf-8 python docs/value/optimize-chatviga/scripts/summarize_final.py
"""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_configs import metric, paired, percentiles  # noqa: E402

DIR = Path(__file__).resolve().parents[1] / "ket-qua"
OUT = DIR / "cuoi"
CELLS = [
    ("A_on", "F_A_on", "RRF tối ưu", "bật luôn"),
    ("A_off", "F_A_off", "RRF tối ưu", "tắt luôn"),
    ("A_adapt", "F_A_adapt", "RRF tối ưu", "thích ứng"),
    ("B_on", "F_B_on", "RRF + rerank tối ưu", "bật luôn"),
    ("B_off", "F_B_off", "RRF + rerank tối ưu", "tắt luôn"),
    ("B_adapt", "F_B_adapt", "RRF + rerank tối ưu", "thích ứng"),
    ("C_cut5", "F_C_cut5", "RRF tối ưu, chỉ cắt 5 mục (không rerank)", "bật luôn"),
    ("B_full", "F_B_full_on", "RRF + rerank đầy đủ (không hạn giờ)", "bật luôn"),
    ("C_off", "F_C_cut5_off", "RRF tối ưu, chỉ cắt 5 mục (không rerank)", "tắt luôn"),
]
QUALITY = [
    ("ctx_recall", "Context Recall"), ("ctx_precision", "Context Precision"), ("hit1", "Hit@1"), ("hit3", "Hit@3"), ("hit5", "Hit@5"), ("mrr", "MRR"),
    ("độ_phủ_ý_bắt_buộc", "Phủ ý bắt buộc"), ("faithfulness", "Faithfulness"), ("judge_dung", "Đúng (1-5)"), ("judge_du_y", "Đủ ý (1-5)"),
    ("judge_lien_quan", "Liên quan (1-5)"), ("đúng_và_có_căn_cứ", "North Star"), ("loại_đúng", "Đúng loại phản hồi"), ("lỗi", "Tỉ lệ lỗi"),
    ("số_mục_cung_cấp", "Số mục vào LLM"), ("token_vào", "Token vào"), ("chi_phí_usd", "Chi phí/câu (USD)"),
]
STEPS = ["giây_router", "giây_rewrite", "giây_embed", "giây_truy_hồi", "giây_rerank", "giây_trả_lời", "giây_kiểm_trích_dẫn"]


def mean_of(rows: list[dict], name: str) -> float | None:
    values = [v for v in (metric(r, name) for r in rows) if v is not None]
    return statistics.mean(values) if values else None


def doc_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("route_kỳ_vọng") == "document" and r.get("loại_kỳ_vọng") == "ANSWER"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {}
    for cell, label, retrieval, thinking in CELLS:
        path = DIR / label / "điểm_lượt_1.jsonl"
        if not path.exists():
            continue
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        answered = doc_rows(rows)
        slices = {"tất_cả_câu_có_đáp_án": answered, "câu_một_ý": [r for r in answered if r.get("loại_câu") == "đơn"], "câu_nhiều_ý": [r for r in answered if r.get("loại_câu") == "kép"]}
        document = [r for r in rows if r.get("route_thực") == "document"]
        data[cell] = {
            "nhãn": label, "truy_hồi": retrieval, "suy_luận": thinking, "số_câu": len(rows),
            "chất_lượng": {name: {s: mean_of(rs, name) for s, rs in slices.items()} for name, _ in QUALITY},
            "độ_trễ_luồng_tài_liệu": percentiles([r["tổng_giây"] for r in document]),
            "độ_trễ_mọi_luồng": percentiles([r["tổng_giây"] for r in rows]),
            "độ_trễ_câu_một_ý": percentiles([r["tổng_giây"] for r in document if r.get("loại_câu") == "đơn"]),
            "độ_trễ_câu_nhiều_ý": percentiles([r["tổng_giây"] for r in document if r.get("loại_câu") == "kép"]),
            "bước_giây_tb": {s: (statistics.mean(r.get(s) or 0 for r in document) if document else None) for s in STEPS},
            "thinking_token_tb": statistics.mean(r.get("thinking_token_trả_lời") or 0 for r in document) if document else None,
            "chi_phí_mỗi_câu_mọi_luồng": statistics.mean(r.get("chi_phí_usd") or 0 for r in rows),
        }
    comparisons = []
    pairs = [("A_on", "A_off"), ("A_on", "A_adapt"), ("B_on", "B_off"), ("B_on", "B_adapt"), ("A_on", "B_on"), ("A_adapt", "B_adapt"), ("A_off", "B_off"), ("A_on", "C_cut5"), ("C_cut5", "B_full"), ("A_on", "B_full"), ("A_on", "C_off"), ("C_cut5", "C_off")]
    for base, test in pairs:
        if base not in data or test not in data:
            continue
        a = [json.loads(line) for line in (DIR / data[base]["nhãn"] / "điểm_lượt_1.jsonl").read_text(encoding="utf-8").splitlines()]
        b = [json.loads(line) for line in (DIR / data[test]["nhãn"] / "điểm_lượt_1.jsonl").read_text(encoding="utf-8").splitlines()]
        entry = {"cơ_sở": base, "thử": test, "chỉ_số": {}}
        for name in ("đúng_và_có_căn_cứ", "judge_dung", "faithfulness", "hit1", "độ_phủ_ý_bắt_buộc", "tổng_giây"):
            rows_a, rows_b = (doc_rows(a), doc_rows(b)) if name != "tổng_giây" else ([r for r in a if r.get("route_thực") == "document"], [r for r in b if r.get("route_thực") == "document"])
            entry["chỉ_số"][name] = paired(rows_a, rows_b, name)
        comparisons.append(entry)
    (OUT / "tong_hop.json").write_text(json.dumps({"ô": data, "so_sánh_cặp": comparisons}, ensure_ascii=False, indent=1, default=float), encoding="utf-8")

    def pct(v: float | None) -> str:
        return "n/a" if v is None else f"{v:.1%}"

    lines = ["## Ma trận 2 × 3 trên tập kiểm 50 câu (câu tài liệu có đáp án)", "", "| Chỉ số | " + " | ".join(f"{c} ({d['truy_hồi']}, {d['suy_luận']})" for c, d in data.items()) + " |", "|---|" + "---|" * len(data)]
    for name, label in QUALITY:
        percent = name not in {"judge_dung", "judge_du_y", "judge_lien_quan", "mrr", "số_mục_cung_cấp", "token_vào", "chi_phí_usd"}
        cells = []
        for d in data.values():
            v = d["chất_lượng"][name]["tất_cả_câu_có_đáp_án"]
            cells.append("n/a" if v is None else (pct(v) if percent else f"{v:.4g}"))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", "## Độ trễ luồng tài liệu (giây)", "", "| Ô | n | P50 | P95 | Trung bình | P50 câu một ý | P50 câu nhiều ý | Suy luận (token) |", "|---|---|---|---|---|---|---|---|"]
    for c, d in data.items():
        t, s1, s2 = d["độ_trễ_luồng_tài_liệu"], d["độ_trễ_câu_một_ý"], d["độ_trễ_câu_nhiều_ý"]
        lines.append(f"| {c} | {t.get('n')} | {t.get('p50', 0):.2f} | {t.get('p95', 0):.2f} | {t.get('trung_bình', 0):.2f} | {s1.get('p50', 0):.2f} | {s2.get('p50', 0):.2f} | {d['thinking_token_tb']:.0f} |")
    lines += ["", "## So sánh cặp", "", "| Cơ sở → thử | Chỉ số | Δ | 95% CI | p (t cặp) |", "|---|---|---|---|---|"]
    for entry in comparisons:
        for name, cmp in entry["chỉ_số"].items():
            if cmp:
                lines.append(f"| {entry['cơ_sở']} → {entry['thử']} | {name} | {cmp['delta']:+.3f} | [{cmp['delta_ci95'][0]:+.3f}, {cmp['delta_ci95'][1]:+.3f}] | {cmp['p_t_cặp']:.4f} |")
    (OUT / "tong_hop.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
