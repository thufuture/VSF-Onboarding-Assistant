"""So khớp trích dẫn với nội dung mục tài liệu (INV13) và làm sạch trích dẫn để hiển thị.

Nội dung mục lưu dưới dạng Markdown phẳng (`* CV. * Lý lịch...`, `\\*\\*`, `##`). Mô hình khi trích thường bỏ ký hiệu danh sách, nên so
khớp từng chữ trên văn bản thô làm câu trả lời đúng bị loại oan (lúc đúng lúc "chưa có căn cứ"). Hai bên được đưa về cùng một dạng
chỉ còn chữ: bỏ ký hiệu Markdown, bỏ gạch chéo thoát, gộp khoảng trắng, không phân biệt hoa thường. Nội dung chữ vẫn phải khớp nguyên
văn nên không thể bịa thêm.
"""

from __future__ import annotations

import re
import unicodedata

_MARKUP = re.compile(r"[*`>#_]+")
_DOTS = re.compile(r"[•·]")
_BULLET = re.compile(r"(?m)^\s*[-+]\s+")
_INLINE_BULLET = re.compile(r"(^|\s)\*\s+")
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~<])")


def normalize_for_match(text: str) -> str:
    cleaned = unicodedata.normalize("NFC", text).replace("\\", "")
    cleaned = _BULLET.sub(" ", cleaned)
    cleaned = _MARKUP.sub("", cleaned)  # xóa hẳn (không thành khoảng trắng): "**3 tháng**)." phải khớp "3 tháng)."
    cleaned = _DOTS.sub(" ", cleaned)
    return " ".join(cleaned.split()).lower()


def quote_matches(quote: str, content: str) -> bool:
    needle = normalize_for_match(quote)
    return bool(needle) and needle in normalize_for_match(content)


def unescape_markdown(text: str) -> str:
    """Bỏ gạch chéo thoát do bộ đọc tài liệu thêm vào (`VinIT\\_BO`, `\\(CCCD\\)`) mà mô hình hay chép nguyên, để câu hiện ra sạch."""
    return _ESCAPE.sub(r"\1", text)


def tidy_quote(quote: str) -> str:
    """Trích dẫn để hiển thị: bỏ gạch thoát và `**`, đổi `* ` đầu mục thành dấu chấm tròn, gộp khoảng trắng."""
    text = unicodedata.normalize("NFC", quote).replace("\\", "").replace("**", "")
    text = _INLINE_BULLET.sub(lambda m: f"{m.group(1)}• ", text)
    return " ".join(text.split())
