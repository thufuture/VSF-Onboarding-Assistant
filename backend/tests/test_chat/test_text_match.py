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
