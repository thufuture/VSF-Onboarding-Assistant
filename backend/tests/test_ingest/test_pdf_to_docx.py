"""PDF scan đã OCR (ảnh trang + chữ vô hình) vẫn chuyển được thành Word có chữ thật, đúng thứ tự dòng."""

import io
import zipfile

import pytest

pymupdf = pytest.importorskip("pymupdf")
pytest.importorskip("pdf2docx")

from src.services.ingest.pdf_to_docx import PdfToWordError, convert_pdf_to_docx  # noqa: E402

LINES = [
    ("Thong bao dot tiep nhan thang 10", 80, 22),
    ("Dot tiep nhan nhan su moi dien ra tai Phong dao tao tang 3.", 130, 11),
    ("Vui long mang can cuoc cong dan ban goc.", 160, 11),
]


def make_ocr_pdf() -> bytes:
    """Giống đầu ra của OCRmyPDF: một ảnh phủ trang, chữ đặt lên ở chế độ vô hình (render_mode=3)."""
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    pixmap = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, 60, 80), False)
    pixmap.set_rect(pixmap.irect, (245,))
    page.insert_image(page.rect, pixmap=pixmap)
    for text, top, size in LINES:
        page.insert_text((60, top), text, fontsize=size, render_mode=3)
    return bytes(document.tobytes())


def docx_text(content: bytes) -> str:
    from lxml import etree

    root = etree.fromstring(zipfile.ZipFile(io.BytesIO(content)).read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return "\n".join("".join(p.itertext()) for p in root.iterfind(".//w:p", ns))


def test_ocr_pdf_becomes_word_with_real_text_in_reading_order() -> None:
    text = docx_text(convert_pdf_to_docx(make_ocr_pdf(), max_pages=10, ocr=True))

    positions = [text.find("dao tao"), text.find("can cuoc")]
    assert text.find("Thong bao") != -1
    assert -1 not in positions and positions == sorted(positions)


def test_page_limit_is_still_enforced_for_ocr_pdf() -> None:
    with pytest.raises(PdfToWordError):
        convert_pdf_to_docx(make_ocr_pdf(), max_pages=0, ocr=True)
