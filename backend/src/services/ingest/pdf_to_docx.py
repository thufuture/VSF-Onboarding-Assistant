"""Chuyển PDF sang Word (.docx) giữ bố cục gần giống bản gốc để HR sửa như trong Word.

Dùng `pdf2docx` (MIT) phân tích bố cục từng trang thành đoạn văn, bảng, ảnh thật (không phải khung chữ trôi nổi như bộ chuyển
PDF sang Word của ONLYOFFICE). Thư viện này dựa trên PyMuPDF (AGPL hoặc giấy phép thương mại của Artifex): cần cân nhắc pháp lý
trước khi bật `PDF_TO_WORD_ENABLED` trên production, xem docs/value/soan-thao-word-va-embedding-local/.

pdf2docx chia mỗi trang thành một "mục" riêng (section) trong file Word; trình soạn thảo xếp chúng thành các trang lệch nhau (đo
thật: PUB_R03 25 trang thành 28). Ta bỏ các ngắt mục trung gian để văn bản chảy liền như một tài liệu Word bình thường (đo thật:
25 trang thành 27, câu chữ và kiểu chữ giữ nguyên).
"""

from __future__ import annotations

import io
import logging
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS = {"w": _W}


class PdfToWordError(Exception):
    """PDF không chuyển được (hỏng, quá nhiều trang, hoặc không có lớp chữ)."""


def _drop_intermediate_sections(docx: bytes) -> bytes:
    """Bỏ mọi ngắt mục nằm trong đoạn văn; chỉ giữ `sectPr` cuối của thân tài liệu."""
    source = zipfile.ZipFile(io.BytesIO(docx))
    root = etree.fromstring(source.read("word/document.xml"))
    for section in root.findall(".//w:p/w:pPr/w:sectPr", _NS):
        section.getparent().remove(section)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "word/document.xml":
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(item, data)
    return out.getvalue()


def convert_pdf_to_docx(pdf: bytes, *, max_pages: int) -> bytes:
    """Chuyển đồng bộ (nặng CPU, gọi qua `asyncio.to_thread`). Ném `PdfToWordError` khi không chuyển được."""
    try:
        import pymupdf
        from pdf2docx import Converter
    except ImportError as exc:  # thiếu thư viện: tính năng bị tắt về mặt triển khai
        raise PdfToWordError("thiếu thư viện pdf2docx") from exc

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "in.pdf"
        target = Path(directory) / "out.docx"
        source.write_bytes(pdf)
        try:
            with pymupdf.open(source) as document:  # type: ignore[no-untyped-call]
                pages = len(document)
                has_text = any(page.get_text().strip() for page in document)
        except Exception as exc:
            raise PdfToWordError("không đọc được PDF") from exc
        if pages == 0 or pages > max_pages:
            raise PdfToWordError(f"PDF có {pages} trang, giới hạn {max_pages}")
        if not has_text:
            raise PdfToWordError("PDF không có lớp chữ (cần OCR trước)")
        converter = Converter(str(source))
        try:
            converter.convert(str(target))
        except Exception as exc:
            raise PdfToWordError("pdf2docx không chuyển được") from exc
        finally:
            converter.close()
        content = target.read_bytes()
    return _drop_intermediate_sections(content)
