"""Tách từ tiếng Việt để tạo `lexical_text` dùng cho BM25 (quyết định D3, phase-2.md).

`underthesea` là lựa chọn mặc định; nếu không cài được hoặc lỗi khi chạy (một số máy Windows/CI), lùi về
tách theo âm tiết (khoảng trắng) sau khi chuẩn hóa NFC và chữ thường — đúng đường lui đã ghi trong D3.
"""

from __future__ import annotations

import unicodedata

try:
    from underthesea import word_tokenize as _word_tokenize

    _HAS_UNDERTHESEA = True
except Exception:  # thư viện có thể thiếu hoặc lỗi cài đặt trên một số máy
    _HAS_UNDERTHESEA = False


def to_lexical_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).lower()
    if _HAS_UNDERTHESEA:
        try:
            tokens = _word_tokenize(normalized)
            return " ".join(tokens)
        except Exception:
            pass  # lùi về tách âm tiết bên dưới (D3)
    return " ".join(normalized.split())
