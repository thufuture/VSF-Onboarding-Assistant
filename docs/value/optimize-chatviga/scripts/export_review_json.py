"""Chuyển golden_v0_nhap.jsonl sang golden_v0_duyet.json: JSON có thụt dòng, xếp theo nhóm, mỗi câu có khối `duyệt` để điền.

Chạy từ gốc repo: PYTHONIOENCODING=utf-8 python docs/value/optimize-chatviga/scripts/export_review_json.py
"""

import json
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "bo-cau-hoi"
ORDER = [
    "tài liệu: một sự kiện",
    "tài liệu: câu kép 2 ý",
    "tài liệu: câu kép 3 ý",
    "tài liệu: không có căn cứ",
    "hành trình: công cụ",
    "hành trình: câu kép nhiều công cụ",
    "ngoài phạm vi",
    "thông tin cá nhân",
    "chèn lệnh",
    "xã giao",
]


def to_review(item: dict) -> dict:
    contexts = [f"{c['document']} / {c['heading']} (mục #{c['section_id']})" for c in item["contexts_expected"]]
    out = {
        "id": item["id"],
        "tập": item["tập"],
        "nhóm": item["category"],
        "loại_câu": item["loại_câu"],
        "độ_khó": item["difficulty"],
        "câu_hỏi": item["question"],
        "route_kỳ_vọng": item["route_kỳ_vọng"],
        "loại_phản_hồi_kỳ_vọng": item["loại_phản_hồi"],
    }
    if item.get("persona"):
        out["persona"] = item["persona"]
    if item["route_kỳ_vọng"] == "tool":
        out["công_cụ_kỳ_vọng"] = item.get("tool_kỳ_vọng", [])
        out["tham_số_kỳ_vọng"] = item.get("tham_số_kỳ_vọng", {})
        if item.get("ghi_chú_hệ_thống"):
            out["ghi_chú"] = item["ghi_chú_hệ_thống"]
    if item["route_kỳ_vọng"] == "document" and item["loại_phản_hồi"] == "ANSWER":
        out["đáp_án_chuẩn"] = item["reference_answer"]
        out["ý_bắt_buộc"] = item["must_include"]
        out["trích_dẫn_chuẩn"] = item["quote_chuẩn"]
        out["mục_nguồn"] = contexts
        out["chunk_id_chuẩn"] = item.get("chunks_expected", [])
        out["khoá_ổn_định"] = [c.get("khoá_ổn_định") for c in item["contexts_expected"]]
        also = [f"{o['document']} / {o['heading']} (mục #{o['section_id']})" for group in item.get("contexts_acceptable", []) for o in group]
        weak = [f"{o['document']} / {o['heading']} (mục #{o['section_id']})" for group in item.get("ứng_viên_yếu", []) for o in group]
        old = [f"{o['document']} / {o['heading']} (mục #{o['section_id']})" for group in item.get("nhiễu_bản_cũ", []) for o in group]
        if also:
            out["mục_khác_cũng_chứa_nguyên_văn_đáp_án_(chấp_nhận_khi_chấm)"] = also
        if weak:
            out["ứng_viên_yếu_(chỉ_trùng_ý_bắt_buộc,_người_duyệt_xem)"] = weak[:6]
        if old:
            out["nhiễu_bản_cũ_(không_chấp_nhận)"] = old
    if item["loại_phản_hồi"] == "NO_BASIS":
        out["mục_gần_nhất_(để_kiểm_chứng_không_có_căn_cứ)"] = f"{item.get('mục_gần_nhất', '')} (điểm trùng từ {item.get('điểm_trùng_từ', '')})"
    if item.get("must_not"):
        out["không_được_xuất_hiện"] = item["must_not"]
    out["duyệt"] = {
        "người_1": {"quyết_định": "", "sửa_lại_hoặc_ghi_chú": ""},
        "người_2": {"quyết_định": "", "sửa_lại_hoặc_ghi_chú": ""},
    }
    return out


def main() -> None:
    items = [json.loads(line) for line in (DIR / "golden_v0_nhap.jsonl").read_text(encoding="utf-8").splitlines()]
    items.sort(key=lambda x: (ORDER.index(x["category"]) if x["category"] in ORDER else 99, x["id"]))
    document = {
        "phiên_bản": "v0-nháp",
        "ghi_chú": "Điền 'duyệt.người_1.quyết_định' bằng giữ / sửa / bỏ; nếu sửa thì ghi nội dung ở 'sửa_lại_hoặc_ghi_chú'. Xem README.md để biết cần kiểm gì.",
        "tổng_số_câu": len(items),
        "câu_hỏi": [to_review(item) for item in items],
    }
    (DIR / "golden_v0_duyet.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print("đã ghi golden_v0_duyet.json:", len(items), "câu")


if __name__ == "__main__":
    main()
