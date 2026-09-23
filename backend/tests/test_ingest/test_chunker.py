"""Đơn vị cho chunker.py (mục 8, kế hoạch 2-B): mục ngắn, bảng/danh sách, mục dài, không heading,
heading cụt — không bao giờ trả 0 section hoặc 0 chunk (mục 11.3)."""

from src.services.ingest.chunker import (
    CHUNK_TARGET_TOKENS,
    count_tokens,
    split_into_chunks,
    split_into_sections,
)


def test_splits_by_h1_h2_h3_headings_and_keeps_text_before_first_heading() -> None:
    markdown = "Giới thiệu chung.\n\n# Mục 1\nNội dung mục 1.\n\n## Mục 1.1\nChi tiết.\n\n### Mục 1.1.1\nSâu hơn."

    sections = split_into_sections(markdown)

    assert [s.heading for s in sections] == [None, "Mục 1", "Mục 1.1", "Mục 1.1.1"]
    assert sections[0].content == "Giới thiệu chung."
    assert [s.section_index for s in sections] == [0, 1, 2, 3]


def test_document_without_any_heading_becomes_one_section() -> None:
    markdown = "Chỉ có văn xuôi, không có heading nào cả. Nhiều câu tiếp theo để đủ dài."

    sections = split_into_sections(markdown)

    assert len(sections) == 1
    assert sections[0].heading is None
    assert sections[0].content == markdown


def test_heading_with_no_body_keeps_heading_as_content_not_empty_section() -> None:
    markdown = "# Mục cụt\n\n# Mục có nội dung\nVăn bản ở đây."

    sections = split_into_sections(markdown)

    assert sections[0].heading == "Mục cụt"
    assert sections[0].content == "Mục cụt"  # không rỗng (mục 11.3)
    assert sections[0].token_count > 0


def test_never_returns_zero_sections_for_nonempty_markdown() -> None:
    for markdown in ["một câu duy nhất", "# \n", "\n\n\n"]:
        sections = split_into_sections(markdown)
        assert len(sections) >= 1


def test_short_section_becomes_a_single_chunk() -> None:
    from src.services.ingest.chunker import SectionDraft

    section = SectionDraft(0, "Mục ngắn", "Vài câu ngắn thôi, không cần cắt.", count_tokens("Vài câu ngắn thôi"))

    chunks = split_into_chunks(section)

    assert len(chunks) == 1
    assert chunks[0].content == section.content
    assert chunks[0].heading == "Mục ngắn"


def test_long_section_is_split_into_multiple_chunks_near_target_size() -> None:
    from src.services.ingest.chunker import SectionDraft

    paragraph = " ".join(f"từ{i}" for i in range(80))  # 80 từ mỗi đoạn
    long_content = "\n\n".join([paragraph] * 6)  # 480 từ, nhiều hơn CHUNK_TARGET_TOKENS (256)
    section = SectionDraft(0, "Mục dài", long_content, count_tokens(long_content))

    chunks = split_into_chunks(section)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count > 0
        # cho phép lệch nhẹ vì gộp theo ranh giới đoạn văn, nhưng không được vượt quá xa mục tiêu
        assert chunk.token_count <= CHUNK_TARGET_TOKENS * 1.5


def test_single_paragraph_longer_than_target_is_force_split() -> None:
    from src.services.ingest.chunker import SectionDraft

    one_giant_paragraph = " ".join(f"từ{i}" for i in range(600))  # không có \n\n nào để cắt
    section = SectionDraft(0, None, one_giant_paragraph, count_tokens(one_giant_paragraph))

    chunks = split_into_chunks(section)

    assert len(chunks) >= 2
    total_words = sum(len(c.content.split()) for c in chunks)
    assert total_words == 600  # không mất từ nào khi cắt cưỡng bức


def test_table_and_list_content_kept_verbatim_within_a_chunk() -> None:
    from src.services.ingest.chunker import SectionDraft

    table_md = "| Cột A | Cột B |\n| --- | --- |\n| 1 | 2 |\n\n* Mục một\n* Mục hai"
    section = SectionDraft(0, "Bảng và danh sách", table_md, count_tokens(table_md))

    chunks = split_into_chunks(section)

    assert any("| Cột A | Cột B |" in c.content for c in chunks)
    assert any("* Mục một" in c.content for c in chunks)


def test_empty_section_still_returns_at_least_one_chunk() -> None:
    from src.services.ingest.chunker import SectionDraft

    section = SectionDraft(0, "Chỉ có heading", "Chỉ có heading", count_tokens("Chỉ có heading"))

    chunks = split_into_chunks(section)

    assert len(chunks) >= 1
    assert chunks[0].content
