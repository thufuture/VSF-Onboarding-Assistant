"""Đơn vị cho parser.py (mục 8, kế hoạch 2-B): parse file D03b thật, cổng chất lượng, lỗi file."""

from pathlib import Path

import pytest

from src.services.ingest.parser import ParseError, parse_document

_REPO_ROOT = Path(__file__).resolve().parents[3]
_D03B = (
    _REPO_ROOT
    / "docs"
    / "chatbot-vsf"
    / "data"
    / "documents"
    / "core"
    / ("SYN_D03b_Chinh_sach_nghi_phep_nam_v2024.docx")
)


def test_parse_real_docx_extracts_markdown_with_headings_and_tables() -> None:
    result = parse_document(_D03B)

    assert len(result.markdown) > 1000
    assert "# " in result.markdown  # có heading
    assert "|" in result.markdown  # bảng được giữ lại (dạng Markdown)
    assert len(result.file_checksum) == 64
    assert len(result.content_checksum) == 64
    assert result.size_bytes > 0


def test_parse_is_deterministic_same_file_same_checksums() -> None:
    first = parse_document(_D03B)
    second = parse_document(_D03B)

    assert first.file_checksum == second.file_checksum
    assert first.content_checksum == second.content_checksum


def test_rejects_unsupported_suffix(tmp_path: Path) -> None:
    bad = tmp_path / "malware.exe"
    bad.write_bytes(b"not a real exe, just bytes")

    with pytest.raises(ParseError, match="đuôi file"):
        parse_document(bad)


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="không tìm thấy"):
        parse_document(tmp_path / "khong-ton-tai.docx")


def test_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "rong.md"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ParseError, match="rỗng"):
        parse_document(empty)


def test_rejects_file_over_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import src.services.ingest.parser as parser_module

    monkeypatch.setattr(parser_module, "MAX_FILE_SIZE_BYTES", 10)
    big = tmp_path / "to.md"
    big.write_text("nội dung dài hơn mười byte rất nhiều", encoding="utf-8")

    with pytest.raises(ParseError, match="vượt giới hạn"):
        parse_document(big)


def test_rejects_text_shorter_than_minimum_length(tmp_path: Path) -> None:
    short = tmp_path / "ngan.md"
    short.write_text("Chào bạn.", encoding="utf-8")

    with pytest.raises(ParseError, match="quá ngắn"):
        parse_document(short)


def test_rejects_corrupted_docx_with_clear_error(tmp_path: Path) -> None:
    import secrets

    fake_docx = tmp_path / "hong.docx"
    # Bytes ngẫu nhiên (không phải zip hợp lệ) để MarkItDown ném lỗi thật, thay vì rơi vào bộ đọc văn bản
    # thuần dự phòng (MarkItDown coi mọi chuỗi UTF-8 đọc được là "văn bản", kể cả sai đuôi/hỏng — mục 11.2).
    fake_docx.write_bytes(secrets.token_bytes(2000))

    with pytest.raises(ParseError, match="không đọc được file"):
        parse_document(fake_docx)


def test_has_embedded_images_flag_false_for_text_only_docx() -> None:
    result = parse_document(_D03B)

    assert result.has_embedded_images is False


def test_has_embedded_images_detects_media_folder_in_docx(tmp_path: Path) -> None:
    # Kiểm trực tiếp hàm dò ảnh (không qua MarkItDown, vì dựng một .docx hợp lệ đầy đủ không cần thiết
    # cho việc chỉ kiểm logic "có thư mục word/media/ trong file zip hay không" — mục 11.2).
    import zipfile

    from src.services.ingest.parser import _has_embedded_images

    with_image = tmp_path / "co-anh.docx"
    with zipfile.ZipFile(with_image, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr("word/media/image1.png", b"\x89PNG fake bytes")

    without_image = tmp_path / "khong-anh.docx"
    with zipfile.ZipFile(without_image, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")

    assert _has_embedded_images(with_image, ".docx") is True
    assert _has_embedded_images(without_image, ".docx") is False
    assert _has_embedded_images(tmp_path / "khong-ton-tai.pdf", ".pdf") is False
