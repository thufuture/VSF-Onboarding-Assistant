"""Đọc PDF có chữ thành Markdown có cấu trúc: tiêu đề theo cỡ chữ/độ đậm, danh sách, bỏ tiêu đề trang lặp lại."""

from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")

from src.services.ingest.markdown_patch import patch_markdown  # noqa: E402
from src.services.ingest.parser import parse_document  # noqa: E402
from src.services.ingest.pdf_markdown import normalize_symbol_bullets, pdf_to_markdown  # noqa: E402
from src.services.ingest.structure import analyze_structure  # noqa: E402

BODY = "Noi dung than bai cua tai lieu, viet du dai de duoc coi la mot doan van thong thuong va khong phai tieu de."


def make_pdf(path: Path, pages: int = 3) -> Path:
    document = pymupdf.open()
    for number in range(pages):
        page = document.new_page(width=595, height=842)
        page.insert_text((60, 30), "Cong bao so 1533 hang trang", fontsize=9)  # tiêu đề trang lặp lại
        page.insert_text((300, 825), f"{number + 1}", fontsize=9)  # số trang
        page.insert_text((60, 100), f"Chuong {number + 1} lon", fontsize=20, fontname="hebo")
        page.insert_text((60, 150), "Muc nho in dam", fontsize=11, fontname="hebo")
        page.insert_text((60, 180), BODY, fontsize=11)
        page.insert_text((60, 200), BODY, fontsize=11)
        page.insert_text((60, 240), "• Muc danh sach thu nhat", fontsize=11)
        page.insert_text((60, 258), "• Muc danh sach thu hai", fontsize=11)
        page.insert_text((60, 300), BODY, fontsize=11)
    path.write_bytes(document.tobytes())
    return path


def test_headings_follow_font_size_and_bold(tmp_path: Path) -> None:
    markdown = pdf_to_markdown(make_pdf(tmp_path / "a.pdf"))

    assert "# Chuong 1 lon" in markdown
    assert "## Muc nho in dam" in markdown
    assert markdown.index("# Chuong 1 lon") < markdown.index("## Muc nho in dam") < markdown.index("Noi dung than bai")


def test_bullets_become_list_items_and_page_furniture_is_dropped(tmp_path: Path) -> None:
    markdown = pdf_to_markdown(make_pdf(tmp_path / "a.pdf"))

    assert "- Muc danh sach thu nhat\n- Muc danh sach thu hai" in markdown
    assert "Cong bao so" not in markdown  # lặp ở đầu mọi trang
    assert "\n1\n" not in markdown and "\n3\n" not in markdown  # số trang


def test_parse_document_uses_structure_only_when_enabled(tmp_path: Path) -> None:
    path = make_pdf(tmp_path / "a.pdf")

    flat = parse_document(path, pdf_structure=False)
    structured = parse_document(path, pdf_structure=True)

    assert not any(line.startswith("#") for line in flat.markdown.splitlines())
    _, report = analyze_structure(structured.markdown)
    assert report.method == "HEADINGS" and report.heading_count >= 6
    assert structured.content_checksum != flat.content_checksum


def test_symbol_font_bullets_are_normalised_and_ignored_when_patching() -> None:
    word = f"Tieu de\n\n{chr(0xE12C)} Mot muc dau tien\n{chr(0xE12C)} Mot muc thu hai\n"

    assert normalize_symbol_bullets(word) == "Tieu de\n\n- Mot muc dau tien\n- Mot muc thu hai\n"
    original = "# Tieu de\n\n- Mot muc dau tien\n- Mot muc thu hai\n\n" + " ".join(f"tu{n}" for n in range(60))
    baseline = word + "\n" + " ".join(f"tu{n}" for n in range(60))
    edited = baseline.replace("tu30", "SUA")
    result = patch_markdown(original, baseline, edited)
    assert result.ok and "SUA" in result.markdown and "# Tieu de" in result.markdown
