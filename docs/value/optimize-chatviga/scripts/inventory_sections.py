"""Kiểm kê các mục (section) của kho tài liệu mẫu dùng để sinh golden set. Chỉ đọc tệp, không gọi LLM, không đụng DB.

Chạy từ thư mục gốc repo bằng venv backend:
  PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/inventory_sections.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from src.services.ingest.chunker import split_into_sections  # noqa: E402
from src.services.ingest.parser import ParseError, parse_document  # noqa: E402
from src.services.ingest.structure import analyze_structure  # noqa: E402

DOCS = ROOT / "docs" / "chatbot-vsf" / "data" / "documents"
# Chỉ lấy tệp gốc của dự án; bỏ tệp tạm Word, tệp do mình tạo ra để thử (scan, pdf trùng), tài liệu lỗi/chèn lệnh/luật dài.
PACKS = ("core", "day1")
EXCLUDE_SUBSTR = ("~$", "_scan", "co_header.pdf", "onboarding_header.pdf")
MIN_WORDS = 50


def inventory() -> list[dict]:
    rows: list[dict] = []
    for pack in PACKS:
        for path in sorted((DOCS / pack).iterdir()):
            if path.suffix.lower() not in {".docx", ".pdf"} or any(s in path.name for s in EXCLUDE_SUBSTR):
                continue
            try:
                parsed = parse_document(path, pdf_structure=False)
            except ParseError as error:
                rows.append({"tệp": path.name, "pack": pack, "lỗi": str(error)[:80]})
                continue
            text, report = analyze_structure(parsed.markdown)
            for section in split_into_sections(text):
                words = len(section.content.split())
                if words >= MIN_WORDS:
                    rows.append(
                        {
                            "tệp": path.name,
                            "pack": pack,
                            "mục": section.heading or "(đầu tài liệu)",
                            "chỉ_số": section.section_index,
                            "số_từ": words,
                            "nội_dung": section.content,
                        }
                    )
    return rows


if __name__ == "__main__":
    rows = inventory()
    ok = [r for r in rows if "mục" in r]
    print("tệp lỗi:", [(r["tệp"], r["lỗi"]) for r in rows if "lỗi" in r])
    per_file: dict[str, int] = {}
    for r in ok:
        per_file[r["tệp"]] = per_file.get(r["tệp"], 0) + 1
    print("số mục đủ dài:", len(ok), "trong", len(per_file), "tệp")
    for name, count in sorted(per_file.items()):
        print(f"  {count:3d}  {name}")
    out = Path(__file__).resolve().parents[1] / "bo-cau-hoi" / "kho_muc.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
    print("đã ghi", out)
