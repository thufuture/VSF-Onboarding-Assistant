"""Chia cấu trúc tài liệu thiếu heading (mục 13): luật nhận tiêu đề giả, chất lượng, section phụ, LLM fallback."""

import json

from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.services.ingest.chunker import SectionDraft, count_tokens, split_into_sections
from src.services.ingest.structure import (
    SECTION_MAX_WORDS,
    SUBSECTION_TARGET_WORDS,
    ai_split_markdown,
    analyze_structure,
    apply_ai_headings,
    infer_headings,
    numbered_paragraphs,
    subdivide_sections,
    validate_ai_headings,
)

FILLER = "Nội dung mô tả chi tiết cho phần này của tài liệu hướng dẫn. " * 12


def test_real_headings_are_never_touched_and_rate_good() -> None:
    markdown = f"# Hồ sơ\n\n{FILLER}\n\n## Thiết bị\n\n{FILLER}\n"

    text, report = analyze_structure(markdown)

    assert text == markdown
    assert report.method == "HEADINGS"
    assert report.quality == "GOOD"
    assert report.heading_count == 2
    assert report.warnings == []


def test_bold_only_lines_become_headings_when_there_are_at_least_two() -> None:
    markdown = f"**Hồ sơ cần nộp**\n\n{FILLER}\n\n**Nhận thiết bị**\n\n{FILLER}\n"

    text, report = analyze_structure(markdown)

    assert "## Hồ sơ cần nộp" in text
    assert "## Nhận thiết bị" in text
    assert report.method == "INFERRED"
    assert report.quality == "MEDIUM"
    assert "HEADINGS_INFERRED" in report.warnings
    assert [s.heading for s in split_into_sections(text)] == ["Hồ sơ cần nộp", "Nhận thiết bị"]


def test_a_single_bold_line_is_not_enough_to_infer_structure() -> None:
    markdown = f"**Lưu ý quan trọng**\n\n{FILLER}\n"

    text, report = analyze_structure(markdown)

    assert text == markdown
    assert report.method == "NONE"


def test_numbered_titles_get_levels_but_list_sentences_do_not() -> None:
    markdown = (
        "1. Hồ sơ nhân sự\n\n"
        "Nộp các giấy tờ theo danh sách bên dưới tại phòng nhân sự.\n\n"
        "1.1 Giấy tờ bắt buộc\n\n"
        "1. Mang theo căn cước công dân bản gốc.\n"
        "2. Mang theo ảnh thẻ.\n\n"
        "2. Thiết bị\n\n"
        "Nhận laptop tại tầng 12 và đăng nhập Outlook.\n"
    )

    text, report = infer_headings(markdown)

    assert "## 1. Hồ sơ nhân sự" in text
    assert "### 1.1 Giấy tờ bắt buộc" in text
    assert "## 2. Thiết bị" in text
    # Các bước kết thúc bằng dấu chấm là danh sách, không phải tiêu đề.
    assert "1. Mang theo căn cước công dân bản gốc." in text.splitlines()
    assert report == 3


def test_consecutive_short_numbered_items_are_a_list_not_headings() -> None:
    markdown = "Chuẩn bị:\n\n1. Căn cước\n2. Ảnh thẻ\n3. Sổ bảo hiểm\n\nSau đó nộp tại phòng nhân sự.\n"

    text, found = infer_headings(markdown)

    assert found == 0
    assert text == markdown


def test_all_caps_title_needs_blank_lines_around_it() -> None:
    markdown = (
        f"QUY ĐỊNH CHUNG\n\n{FILLER}\n\nTHIẾT BỊ VÀ TÀI KHOẢN\n\n{FILLER}\n\nCHỮ HOA NHƯNG NẰM NGAY\nSÁT DÒNG KẾ TIẾP\n"
    )

    text, found = infer_headings(markdown)

    assert found == 2
    assert "## QUY ĐỊNH CHUNG" in text
    assert "## THIẾT BỊ VÀ TÀI KHOẢN" in text
    assert "## CHỮ HOA NHƯNG NẰM NGAY" not in text


def test_long_text_without_any_structure_is_rated_poor_and_short_text_is_fine() -> None:
    long_text = "\n".join(f"Dòng nội dung thứ {i} của một tài liệu không có tiêu đề nào cả." for i in range(60))
    short_text = "Một đoạn ngắn không cần chia mục."

    _, poor = analyze_structure(long_text)
    _, fine = analyze_structure(short_text)

    assert poor.quality == "POOR"
    assert "NO_STRUCTURE" in poor.warnings
    assert fine.quality == "GOOD"
    assert fine.method == "NONE"


def test_analyze_without_infer_only_measures() -> None:
    markdown = f"**Mục một**\n\n{FILLER}\n\n**Mục hai**\n\n{FILLER}\n"

    text, report = analyze_structure(markdown, infer=False)

    assert text == markdown
    assert report.method == "NONE"


def test_long_section_is_split_into_numbered_subsections_without_changing_words() -> None:
    paragraphs = [f"Đoạn {i} " + "từ " * 90 for i in range(20)]
    section = SectionDraft(0, "Hồ sơ", "\n\n".join(paragraphs), count_tokens(" ".join(paragraphs)))
    assert section.token_count > SECTION_MAX_WORDS

    result = subdivide_sections([section, SectionDraft(1, "Ngắn", "Nội dung ngắn.", 3)])

    assert len(result) > 2
    assert result[0].heading == "Hồ sơ (phần 1)"
    assert result[1].heading == "Hồ sơ (phần 2)"
    assert result[-1].heading == "Ngắn"
    assert [s.section_index for s in result] == list(range(len(result)))
    assert max(s.token_count for s in result[:-1]) <= SUBSECTION_TARGET_WORDS + 100
    joined = " ".join(s.content for s in result[:-1])
    assert joined.split() == " ".join(paragraphs).split()


def test_one_giant_paragraph_with_line_breaks_is_split_by_line() -> None:
    lines = [f"Dòng {i} " + "chữ " * 60 for i in range(40)]
    section = SectionDraft(0, None, "\n".join(lines), count_tokens(" ".join(lines)))

    result = subdivide_sections([section])

    assert len(result) > 3
    assert result[0].heading == "Phần 1"


def test_short_sections_are_left_alone() -> None:
    sections = [SectionDraft(0, "A", "ngắn", 1), SectionDraft(1, "B", "cũng ngắn", 2)]

    assert subdivide_sections(sections) == sections


# --- LLM fallback: code kiểm mọi đề xuất ---

DOC = "\n".join(f"Dòng {i} của tài liệu." for i in range(1, 11))


def raw(*items: dict[str, object]) -> str:
    return json.dumps({"headings": list(items)}, ensure_ascii=False)


def test_valid_ai_headings_pass() -> None:
    parsed = validate_ai_headings(
        raw({"paragraph": 1, "level": 1, "title": "Mở đầu"}, {"paragraph": 5, "level": 2, "title": "Thiết bị"}), 10
    )

    assert parsed is not None
    assert [(h.paragraph, h.level, h.title) for h in parsed] == [(1, 1, "Mở đầu"), (5, 2, "Thiết bị")]


def test_ai_headings_with_any_defect_are_rejected_entirely() -> None:
    good = {"paragraph": 1, "level": 1, "title": "A"}
    bad_cases = [
        "không phải json",
        raw(good),  # quá ít mục
        raw(good, {"paragraph": 1, "level": 1, "title": "B"}),  # trùng đoạn
        raw({"paragraph": 5, "level": 1, "title": "B"}, {"paragraph": 2, "level": 1, "title": "C"}),  # giảm dần
        raw(good, {"paragraph": 99, "level": 1, "title": "B"}),  # đoạn không tồn tại
        raw(good, {"paragraph": 3, "level": 7, "title": "B"}),  # cấp sai
        raw(good, {"paragraph": 3, "level": 1, "title": "  "}),  # tên rỗng
        raw(good, {"paragraph": 3, "level": 1, "title": "x" * 300}),  # tên quá dài
        raw(*[{"paragraph": i, "level": 1, "title": f"T{i}"} for i in range(1, 11)]),  # quá nhiều so với độ dài
        json.dumps({"headings": "sai kiểu"}),
    ]
    for case in bad_cases:
        assert validate_ai_headings(case, 10) is None, case


def test_apply_ai_headings_keeps_every_original_line() -> None:
    paragraphs = numbered_paragraphs(DOC)
    parsed = validate_ai_headings(
        raw({"paragraph": 1, "level": 1, "title": "Mở đầu"}, {"paragraph": 6, "level": 2, "title": "Phần sau"}), 10
    )
    assert parsed is not None

    result = apply_ai_headings(DOC, paragraphs, parsed)

    assert result is not None
    lines = result.markdown.splitlines()
    assert lines[0] == "# Mở đầu"
    assert "## Phần sau" in lines
    assert [line for line in lines if not line.startswith("#")] == DOC.splitlines()
    sections = split_into_sections(result.markdown)
    assert [s.heading for s in sections] == ["Mở đầu", "Phần sau"]


async def test_ai_split_applies_valid_response_and_survives_failures() -> None:
    ok = FakeChatCompletion(
        raw({"paragraph": 1, "level": 1, "title": "Mở đầu"}, {"paragraph": 6, "level": 1, "title": "Tiếp theo"})
    )
    result = await ai_split_markdown(DOC, ok)
    assert result is not None
    assert [h.title for h in result.headings] == ["Mở đầu", "Tiếp theo"]

    assert await ai_split_markdown(DOC, FakeChatCompletion("không phải json")) is None
    assert await ai_split_markdown("chỉ một dòng", ok) is None  # quá ít đoạn để chia

    def boom(_system: str, _user: str) -> str:
        raise RuntimeError("mạng lỗi")

    assert await ai_split_markdown(DOC, FakeChatCompletion(boom)) is None
