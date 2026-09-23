"""Đơn vị cho lexical.py (quyết định D3, phase-2.md): tách từ, chuẩn hóa NFC/chữ thường."""

from src.services.ingest.lexical import to_lexical_text


def test_lowercases_and_normalizes_nfc() -> None:
    result = to_lexical_text("NGHỈ PHÉP Năm")

    assert result == result.lower()
    assert "nghỉ" in result
    assert "phép" in result


def test_tokenizes_vietnamese_compound_words_when_underthesea_available() -> None:
    result = to_lexical_text("nghỉ phép năm")

    # underthesea thường gộp "nghỉ phép" thành một token; chỉ kiểm không rỗng và giữ đủ nghĩa,
    # không khóa cứng vào một cách tách cụ thể (có thể đổi khi nâng cấp thư viện).
    assert result
    assert "phép" in result or "nghỉ_phép" in result


def test_empty_string_returns_empty() -> None:
    assert to_lexical_text("") == ""


def test_deterministic_same_input_same_output() -> None:
    text = "Trưởng phòng phê duyệt đơn nghỉ phép từ 5 ngày liên tục trở lên."

    assert to_lexical_text(text) == to_lexical_text(text)
