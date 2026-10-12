"""Bổ sung nhãn mức CHUNK và kiểm độ mơ hồ của nhãn cho golden_v0_nhap.jsonl.

Với mỗi ý (trích dẫn chuẩn) của câu tài liệu:
- `chunks_expected`: chunk (đơn vị Viga thực sự truy hồi) của mục chuẩn có chứa trích dẫn / ý bắt buộc;
- `contexts_acceptable`: các mục KHÁC cũng trả lời được (chứa nguyên văn trích dẫn hoặc đủ mọi ý bắt buộc), ví dụ tài liệu trùng hoặc
  bản cũ nêu lại cùng thông tin; khi chấm truy hồi các mục này được tính là đúng; nếu thông tin khác nhau thì là nhiễu mâu thuẫn cần người xem;
- `khoá_ổn_định`: tên nguồn + tiêu đề + mã băm nội dung, để nhãn không hỏng khi nạp lại tài liệu (mã mục trong DB đổi theo lần nạp).

Chạy từ gốc repo: PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/enrich_chunk_labels.py
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
from src.services.text_match import normalize_for_match, quote_matches  # noqa: E402

DIR = Path(__file__).resolve().parents[1] / "bo-cau-hoi"


def stable_key(section: dict) -> str:
    digest = hashlib.sha256(normalize_for_match(section["content"]).encode()).hexdigest()[:10]
    return f"{section['source_key']}|{section['heading']}|{digest}"


def main() -> None:
    sections = {s["section_id"]: s for s in json.loads((DIR / "kho_muc_dev.json").read_text(encoding="utf-8"))}
    chunks = json.loads((DIR / "kho_chunk_dev.json").read_text(encoding="utf-8"))
    by_section: dict[int, list[dict]] = {}
    for chunk in chunks:
        by_section.setdefault(chunk["section_id"], []).append(chunk)
    orphans = [c["chunk_id"] for c in chunks if c["section_id"] not in sections]
    print(f"chunk: {len(chunks)} | mục: {len(sections)} | chunk không thuộc mục nào trong kho: {orphans}")
    print("số chunk trên mỗi mục:", {n: sum(1 for v in by_section.values() if len(v) == n) for n in sorted({len(v) for v in by_section.values()})})

    items = [json.loads(line) for line in (DIR / "golden_v0_nhap.jsonl").read_text(encoding="utf-8").splitlines()]
    # Mã mục trong DB đổi mỗi lần nạp lại tài liệu: gắn lại nhãn theo khoá ổn định (nguồn + tiêu đề + mã băm nội dung)
    by_key = {stable_key(s): s for s in sections.values()}
    remapped, lost = 0, []
    for item in items:
        for context in item["contexts_expected"]:
            if context["section_id"] in sections and stable_key(sections[context["section_id"]]) == context.get("khoá_ổn_định", stable_key(sections[context["section_id"]])):
                continue
            target = by_key.get(context.get("khoá_ổn_định", ""))
            if target:
                context.update(section_id=target["section_id"], section_index=target["section_index"], heading=target["heading"])
                context["tương_đương_section_id"] = [s["section_id"] for s in sections.values() if s["section_id"] != target["section_id"] and stable_key(s) == stable_key(target)]
                remapped += 1
            else:
                lost.append(item["id"])
    print(f"gắn lại nhãn theo khoá ổn định: {remapped} | nhãn mất mục nguồn (cần người xem): {sorted(set(lost))}")
    stats = {"ý": 0, "quote_trong_1_chunk": 0, "quote_trải_nhiều_chunk_hoặc_không_khớp": 0, "có_mục_chấp_nhận_khác": 0, "mục_khác_chứa_cùng_thông_tin_không_phải_trùng": 0}
    ambiguous: list[str] = []
    for item in items:
        item["chunks_expected"] = []
        item["contexts_acceptable"] = []
        for context, quote in zip(item["contexts_expected"], item["quote_chuẩn"], strict=False):
            stats["ý"] += 1
            section = sections[context["section_id"]]
            context["khoá_ổn_định"] = stable_key(section)
            matching = [c["chunk_id"] for c in by_section.get(context["section_id"], []) if quote_matches(quote, c["content"])]
            item["chunks_expected"].append(matching)
            stats["quote_trong_1_chunk" if matching else "quote_trải_nhiều_chunk_hoặc_không_khớp"] += 1
            own = {context["section_id"], *context["tương_đương_section_id"]}
            idea_must = [m for m in item["must_include"] if quote_matches(m, section["content"])]
            others = []
            weak = []
            for other in sections.values():
                if other["section_id"] in own:
                    continue
                entry = {"section_id": other["section_id"], "document": other["document_title"], "heading": other["heading"], "khoá_ổn_định": stable_key(other)}
                if quote_matches(quote, other["content"]):
                    others.append(entry)  # chứa NGUYÊN VĂN trích dẫn chuẩn: đáp án đúng ở mục khác (chấp nhận khi chấm truy hồi)
                elif idea_must and all(quote_matches(m, other["content"]) for m in idea_must):
                    weak.append(entry)  # chỉ trùng các cụm "ý bắt buộc" (có thể là cụm chung như tên phòng ban): người duyệt xem, KHÔNG tự chấp nhận
            item.setdefault("ứng_viên_yếu", []).append(weak)
            # tài liệu "bản cũ, đã thay thế" nêu lại cùng thông tin là NHIỄU (không chấp nhận làm đáp án đúng), tách riêng
            old = [o for o in others if "ban_cu_da_thay_the" in o["document"]]
            acceptable = [o for o in others if o not in old]
            item["contexts_acceptable"].append(acceptable)
            item.setdefault("nhiễu_bản_cũ", []).append(old)
            if acceptable:
                stats["có_mục_chấp_nhận_khác"] += 1
                ambiguous.append(f"{item['id']}: {[o['document'] + ' / ' + str(o['heading']) for o in acceptable]}")
            if old:
                stats["mục_khác_chứa_cùng_thông_tin_không_phải_trùng"] += 1
    (DIR / "golden_v0_nhap.jsonl").write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n", encoding="utf-8")
    print(stats)
    for line in ambiguous[:20]:
        print("  mục khác cũng trả lời được ->", line)


if __name__ == "__main__":
    main()
