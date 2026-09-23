"""Đọc file (.docx/.pdf/.md) và trả về Markdown thuần cùng hai checksum.

Mục 11.1/11.2 của kế hoạch 2-B: chặn đuôi lạ, file rỗng/quá lớn, file hỏng; cổng chất lượng tối thiểu
(chữ quá ngắn = có thể là file scan, chưa OCR ở Phase 2); gắn cờ cảnh báo khi tài liệu có ảnh nhúng
(không xử lý ảnh, chỉ cảnh báo — xem mục 11.2).
"""

from __future__ import annotations

import hashlib
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

from markitdown import MarkItDown

ALLOWED_SUFFIXES = {".docx", ".pdf", ".md"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB (mục 11.1)
MIN_TEXT_LENGTH = 200  # dưới ngưỡng này coi như có thể là file scan (system-design mục 5.1)


class ParseError(Exception):
    """File không đọc được hoặc không đạt cổng chất lượng tối thiểu (mục 11.1/11.2)."""


@dataclass(frozen=True)
class ParsedDocument:
    markdown: str
    file_checksum: str
    content_checksum: str
    size_bytes: int
    has_embedded_images: bool


def parse_document(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ParseError(f"đuôi file không được hỗ trợ: '{suffix}' (chỉ nhận {sorted(ALLOWED_SUFFIXES)})")
    if not path.is_file():
        raise ParseError(f"không tìm thấy file: {path}")

    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise ParseError("file rỗng")
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise ParseError(f"file vượt giới hạn {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB ({size_bytes} byte)")

    raw = path.read_bytes()
    file_checksum = hashlib.sha256(raw).hexdigest()

    try:
        result = MarkItDown().convert(str(path))
    except Exception as exc:  # thư viện ngoài có thể ném nhiều loại lỗi khác nhau khi file hỏng/sai định dạng
        raise ParseError(f"không đọc được file (có thể hỏng hoặc sai định dạng): {exc}") from exc

    markdown = unicodedata.normalize("NFC", result.text_content or "")
    if len(markdown.strip()) < MIN_TEXT_LENGTH:
        raise ParseError(
            f"nội dung quá ngắn ({len(markdown.strip())} ký tự, cần >= {MIN_TEXT_LENGTH}) — "
            "có thể là file scan; OCR chưa bật ở Phase 2 (xem Phase 5)"
        )

    content_checksum = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return ParsedDocument(
        markdown=markdown,
        file_checksum=file_checksum,
        content_checksum=content_checksum,
        size_bytes=size_bytes,
        has_embedded_images=_has_embedded_images(path, suffix),
    )


def _has_embedded_images(path: Path, suffix: str) -> bool:
    """Dò ảnh nhúng trong .docx (mục 11.2): chỉ để cảnh báo trong quality_report, không xử lý ảnh."""
    if suffix != ".docx":
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return any(name.startswith("word/media/") for name in archive.namelist())
    except zipfile.BadZipFile:
        return False
