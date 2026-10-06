"""So khớp trích dẫn đã chuẩn hóa: bỏ ký hiệu Markdown nhưng vẫn đòi đúng chữ (INV13)."""

import pytest

from src.services.text_match import normalize_for_match, quote_matches, tidy_quote

_CONTENT = (
    "## 2. Hồ sơ ngày đầu\n"
    "* CV.\n"
    "* Lý lịch tư pháp (bản chính, còn hạn **3 tháng**).\n"
    "* Căn cước công dân \\(CCCD\\) bản gốc.\n"
)


@pytest.mark.parametrize(
    "quote",
    [
        "CV. Lý lịch tư pháp (bản chính, còn hạn 3 tháng).",
        "* CV. * Lý lịch tư pháp (bản chính, còn hạn **3 tháng**).",
        "căn cước công dân (cccd) bản gốc",
        "Lý  lịch tư pháp",
    ],
)
def test_quote_that_differs_only_by_markup_or_case_matches(quote: str) -> None:
    assert quote_matches(quote, _CONTENT)


@pytest.mark.parametrize(
    "quote",
    [
        "Lý lịch tư pháp còn hạn 6 tháng",
        "Hộ chiếu bản gốc",
        "",
        "**",
    ],
)
def test_quote_with_different_words_or_only_markup_does_not_match(quote: str) -> None:
    assert not quote_matches(quote, _CONTENT)


def test_normalization_removes_escapes_bullets_and_collapses_spaces() -> None:
    assert normalize_for_match("* A\n  - B   \\*\\*C\\*\\*") == "a b c"


def test_tidy_quote_turns_inline_stars_into_bullets_and_drops_bold_marks() -> None:
    assert tidy_quote("* CV. * Lý lịch **quan trọng** \\(bản chính\\)") == "• CV. • Lý lịch quan trọng (bản chính)"


# Nội dung thật của "Hướng dẫn ngày 1" dạng docx không tiêu đề: dấu `-` và `+` đầu dòng, `\*` thoát, dòng chỉ có `\*\*`.
_DOCX_LIKE = (
    "Ngày đầu onboarding\n"
    "Chuẩn bị hồ sơ phải nộp trong ngày đầu:\n"
    "- CV.\n"
    "- Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp.\n"
    "- Căn cước công dân bản Photo.\n"
    "\\* Đầu mối liên hệ: Phòng tuyển dụng.\n"
    "\\*\\*\n"
    "Điều kiện được tính hoàn thành:\n"
    "+ Điểm danh đầu giờ.\n"
    "+ Hoàn thành và đạt >= 80% bài test cuối khóa.\n"
    "Trường hợp máy đã có Ubuntu sẵn\n"
    "- đang sử dụng sẵn Ubuntu OS , có thể xin phê duyệt qua Team."
)


def test_cleaned_multiline_quote_with_dash_and_plus_bullets_still_matches_the_source() -> None:
    quote = "Chuẩn bị hồ sơ phải nộp trong ngày đầu:\n- CV.\n- Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp."
    shown = tidy_quote(quote)
    assert "\n" not in shown and " - CV. - Lý lịch" in shown  # tidy gộp một dòng, dấu `-` nằm lại giữa câu
    assert quote_matches(shown, _DOCX_LIKE)


def test_every_line_range_of_a_real_section_survives_the_tidy_roundtrip() -> None:
    """Quote hiển thị là chuỗi được kiểm lại khi HR bấm tạo task: mọi dải dòng phải khớp lại sau khi làm sạch."""
    lines = [line for line in _DOCX_LIKE.split("\n") if line.strip() and normalize_for_match(line)]
    failures = [
        (first, last)
        for first in range(len(lines))
        for last in range(first, len(lines))
        if not quote_matches(tidy_quote("\n".join(lines[first : last + 1])), _DOCX_LIKE)
    ]
    assert failures == []


def test_lone_dash_removal_does_not_make_different_words_match() -> None:
    assert not quote_matches("- CV. - Hộ chiếu", _DOCX_LIKE)
    assert not quote_matches("Điểm danh cuối giờ", _DOCX_LIKE)
