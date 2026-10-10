"""Đo (1) bộ đọc PDF cũ so với bộ đọc có cấu trúc: số mục, số tiêu đề, chất lượng, thời gian, độ giữ chữ;
(2) bước vá Markdown khi HR sửa một chỗ trong bản Word dựng từ PDF: vá được không, đổi bao nhiêu dòng của Markdown gốc.

Chạy trong ảnh backend, gắn mã nguồn mới vào /app/src:
  docker run --rm --cpus 4 -v <repo>/backend/src:/app/src:ro -v <repo>/docs/chatbot-vsf/data/documents:/d:ro \
      -v <repo>/docs/value/benchmark-ocr:/b vsf-onboarding-backend python /b/scripts/do_doc_pdf_va_va_markdown.py /d /b/ket-qua/doc-pdf-va-va.json
"""

import difflib
import json
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, "/app")
from markitdown import MarkItDown

from src.services.ingest.markdown_patch import patch_markdown
from src.services.ingest.parser import parse_document
from src.services.ingest.pdf_markdown import normalize_symbol_bullets, pdf_to_markdown
from src.services.ingest.pdf_to_docx import convert_pdf_to_docx
from src.services.ingest.structure import analyze_structure

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
SKIP_PATCH_OVER_PAGES = 30  # pdf2docx rất chậm với PDF dài; chỉ đo bước vá cho PDF ngắn hơn

rows = []
for pdf in sorted(ROOT.rglob("*.pdf")):
    name = pdf.name
    if "scan" in name.lower() or name.startswith(("SYN_E11", "SYN_E12")):
        continue
    started = time.perf_counter()
    old = unicodedata.normalize("NFC", MarkItDown().convert(str(pdf)).text_content or "")
    t_old = time.perf_counter() - started
    if len(old.strip()) < 200:
        continue
    started = time.perf_counter()
    new = unicodedata.normalize("NFC", pdf_to_markdown(pdf))
    t_new = time.perf_counter() - started
    _, report_old = analyze_structure(old)
    _, report_new = analyze_structure(new)
    vocabulary_old = set(old.split())
    row = {
        "tệp": name,
        "mục_cũ": report_old.section_count,
        "mục_mới": report_new.section_count,
        "tiêu_đề_cũ": report_old.heading_count,
        "tiêu_đề_mới": report_new.heading_count,
        "chất_lượng_cũ": report_old.quality,
        "chất_lượng_mới": report_new.quality,
        "từ_cũ": len(old.split()),
        "từ_mới": len(new.split()),
        "từ_vựng_giữ_%": round(100 * len(vocabulary_old & set(new.split())) / max(1, len(vocabulary_old)), 1),
        "giây_cũ": round(t_old, 2),
        "giây_mới": round(t_new, 2),
    }
    try:
        docx = convert_pdf_to_docx(pdf.read_bytes(), max_pages=SKIP_PATCH_OVER_PAGES)
    except Exception as exc:
        row["vá"] = f"bỏ qua ({type(exc).__name__})"
        rows.append(row)
        print(row, flush=True)
        continue
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "b0.docx"
        path.write_bytes(docx)
        b0 = normalize_symbol_bullets(parse_document(path).markdown)
    marker = next((w for w in b0.split() if len(w) > 5 and w.isalpha()), None)
    b1 = b0.replace(marker, marker + " THEMVAO", 1) if marker else b0
    for label, m in (("cũ", old), ("mới", new)):
        result = patch_markdown(m, b0, b1)
        changed = sum(1 for line in difflib.ndiff(m.splitlines(), result.markdown.splitlines()) if line[:1] in "+-")
        row[f"vá_được_{label}"] = result.ok
        row[f"dòng_đổi_{label}"] = changed if result.ok else None
        row[f"tổng_dòng_{label}"] = len(m.splitlines())
    rows.append(row)
    print(row, flush=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
