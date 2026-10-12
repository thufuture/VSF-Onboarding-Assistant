"""Vá Markdown: chỉ chỗ HR sửa đổi, phần còn lại của Markdown gốc giữ nguyên từng ký tự."""

import random

from src.services.ingest.markdown_patch import patch_markdown

WORDS = [f"{syllable}{n}" for n in range(60) for syllable in ("quy", "dinh", "cong", "doan", "nguoi", "lao")]


def make_words(count: int, seed: int = 1) -> list[str]:
    rng = random.Random(seed)
    return [rng.choice(WORDS) + str(rng.randrange(1000)) for _ in range(count)]


def wrap(words: list[str], width: int) -> str:
    """Xuống dòng sau mỗi `width` từ: cùng một chuỗi từ nhưng ngắt dòng khác nhau, như PDF so với Word."""
    return "\n".join(" ".join(words[i : i + width]) for i in range(0, len(words), width))


def test_single_word_edit_changes_only_that_place() -> None:
    words = make_words(600)
    m = "# Quy chế\n\n" + wrap(words, 9)
    b0 = wrap(words, 14)
    edited = list(words)
    edited[300] = "THAYDOI"
    b1 = wrap(edited, 14)

    result = patch_markdown(m, b0, b1)

    assert result.ok and result.changed
    assert "THAYDOI" in result.markdown and words[300] not in result.markdown.split()
    # Phần xa chỗ sửa giữ nguyên từng ký tự, kể cả cách ngắt dòng riêng của M.
    assert result.markdown.startswith(m[:600]) and result.markdown.endswith(m[-600:])
    assert result.markdown.count("\n") >= m.count("\n") - 2


def test_insertion_and_deletion() -> None:
    words = make_words(500, seed=2)
    m, b0 = wrap(words, 10), wrap(words, 12)
    edited = words[:200] + ["CHENVAO", "MOTCUM", "TUMOI"] + words[200:350] + words[360:]
    result = patch_markdown(m, b0, wrap(edited, 12))
    assert result.ok
    tokens = result.markdown.split()
    assert "CHENVAO" in tokens and "TUMOI" in tokens
    assert all(word not in tokens for word in words[350:360])


def test_two_distant_edits_leave_everything_between_untouched() -> None:
    words = make_words(900, seed=3)
    m, b0 = wrap(words, 8), wrap(words, 13)
    edited = list(words)
    edited[100], edited[700] = "MOT", "HAI"
    result = patch_markdown(m, b0, wrap(edited, 13))
    assert result.ok and result.groups == 2
    middle = " ".join(words[150:650])
    assert middle in " ".join(result.markdown.split())


def test_edit_near_start_and_end_of_document() -> None:
    words = make_words(400, seed=4)
    m, b0 = wrap(words, 7), wrap(words, 11)
    edited = list(words)
    edited[2], edited[-2] = "DAUBAI", "CUOIBAI"
    result = patch_markdown(m, b0, wrap(edited, 11))
    assert result.ok
    tokens = result.markdown.split()
    assert tokens[2] == "DAUBAI" and tokens[-2] == "CUOIBAI"


def test_no_change_returns_the_original_text_untouched() -> None:
    words = make_words(300, seed=5)
    m, b0 = wrap(words, 9), wrap(words, 12)
    result = patch_markdown(m, b0, b0)
    assert result.ok and not result.changed and result.markdown == m


def test_markdown_markup_in_m_does_not_break_matching() -> None:
    words = make_words(400, seed=6)
    m = "## Điều 1\n\n**" + " ".join(words[:5]) + "**\n\n- " + " ".join(words[5:]) + "\n"
    b0 = " ".join(words)
    edited = list(words)
    edited[200] = "SUA"
    result = patch_markdown(m, b0, " ".join(edited))
    assert result.ok and "SUA" in result.markdown
    assert result.markdown.startswith("## Điều 1\n\n**")


def test_unanchorable_edit_in_repeated_text_reports_failure() -> None:
    repeated = ["lap", "lai", "mot", "cum", "tu"] * 120
    m = b0 = " ".join(repeated)
    edited = list(repeated)
    edited[300] = "KHAC"
    result = patch_markdown(m, b0, " ".join(edited))
    assert not result.ok and result.markdown == m
