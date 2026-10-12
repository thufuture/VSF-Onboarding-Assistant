"""Gom số liệu của benchmark cuối thành một tệp JSON cho trang biểu đồ (ket-qua/cuoi/dashboard_data.json).

Đọc: ket-qua/cuoi/tong_hop.json (do summarize_final.py tạo), ket-qua/F_*/điểm_lượt_1.jsonl (độ trễ từng câu), ket-qua/quet-tham-so/*.json.
Chạy: python docs/value/optimize-chatviga/scripts/export_dashboard_data.py
"""

import json
import statistics
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "ket-qua"
CELLS = ["A_on", "A_off", "A_adapt", "B_on", "B_off", "B_adapt", "C_cut5", "B_full", "C_off"]
LABEL = {"A_on": "F_A_on", "A_off": "F_A_off", "A_adapt": "F_A_adapt", "B_on": "F_B_on", "B_off": "F_B_off", "B_adapt": "F_B_adapt", "C_cut5": "F_C_cut5", "B_full": "F_B_full_on", "C_off": "F_C_cut5_off"}


def main() -> None:
    summary = json.loads((DIR / "cuoi" / "tong_hop.json").read_text(encoding="utf-8"))
    out: dict = {"ô": {}, "so_sánh": summary["so_sánh_cặp"]}
    for cell in CELLS:
        data = summary["ô"][cell]
        rows = [json.loads(line) for line in (DIR / LABEL[cell] / "điểm_lượt_1.jsonl").read_text(encoding="utf-8").splitlines()]
        document = [r for r in rows if r.get("route_thực") == "document"]
        out["ô"][cell] = {
            "truy_hồi": data["truy_hồi"],
            "suy_luận": data["suy_luận"],
            "chất_lượng": {k: v["tất_cả_câu_có_đáp_án"] for k, v in data["chất_lượng"].items()},
            "độ_trễ": data["độ_trễ_luồng_tài_liệu"],
            "độ_trễ_câu_một_ý": data["độ_trễ_câu_một_ý"],
            "độ_trễ_câu_nhiều_ý": data["độ_trễ_câu_nhiều_ý"],
            "giây_từng_câu": sorted(round(r["tổng_giây"], 2) for r in document),
            "bước_giây_tb": data["bước_giây_tb"],
            "thinking_token_tb": data["thinking_token_tb"],
            "chi_phí_mỗi_câu_tài_liệu": statistics.mean(r.get("chi_phí_usd") or 0 for r in document),
        }
    rrf = json.loads((DIR / "quet-tham-so" / "rrf.json").read_text(encoding="utf-8"))
    out["quét_rrf"] = [{"cấu_hình": r["cấu_hình"], **r["trung_bình"]} for r in rrf["cấu_hình"]]
    out["quét_rerank"] = {}
    for name, tag in (("bge fp32", ""), ("bge int8", "_int8"), ("mmarco-mMiniLM", "_minilm")):
        path = DIR / "quet-tham-so" / f"rerank{tag}.json"
        if path.exists():
            out["quét_rerank"][name] = json.loads(path.read_text(encoding="utf-8"))["cấu_hình"]
    (DIR / "cuoi" / "dashboard_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("đã ghi dashboard_data.json:", len(json.dumps(out)), "byte")


if __name__ == "__main__":
    main()
