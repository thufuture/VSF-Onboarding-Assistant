"""Tách Markdown thành section (cha, theo heading H1-H3) rồi chunk (con, ~256 từ).

Kế hoạch 2-B mục 4 (cây file) và mục 11.3 (không bao giờ 0 chunk). Đếm token xấp xỉ theo số từ
(quyết định D6 trong phase-2.md), không thêm tiktoken.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CHUNK_TARGET_TOKENS = 256
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


@dataclass(frozen=True)
class SectionDraft:
    section_index: int
    heading: str | None
    content: str
    token_count: int


@dataclass(frozen=True)
class ChunkDraft:
    section_index: int  # ánh xạ lại section cha khi ghi DB; không phải khóa chính cuối cùng
    heading: str | None
    content: str
    token_count: int


def count_tokens(text: str) -> int:
    """Xấp xỉ theo số từ (D6, phase-2.md) — không dùng tiktoken."""
    return len(text.split())


def split_into_sections(markdown: str) -> list[SectionDraft]:
    """Cắt theo heading H1-H3. Không có heading nào -> toàn bộ văn bản là một section (mục 11.3)."""
    raw_sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            # Luôn chốt phần đang gom trước khi mở section mới — kể cả phần văn bản trước heading đầu
            # tiên (current_heading=None), tránh lỗi mất nội dung mở đầu.
            raw_sections.append((current_heading, current_lines))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    raw_sections.append((current_heading, current_lines))

    drafts: list[SectionDraft] = []
    index = 0
    for heading, body_lines in raw_sections:
        content = "\n".join(body_lines).strip()
        if not content:
            if heading is None:
                continue  # phần trước heading đầu tiên rỗng, không tạo section thừa
            content = heading  # heading cụt không có nội dung (mục 11.3): giữ heading làm nội dung, không bỏ
        drafts.append(SectionDraft(index, heading, content, count_tokens(content)))
        index += 1

    if not drafts:
        # Toàn bộ rỗng sau khi lọc (văn bản không có heading và cũng không có đoạn nào) — cổng ở parser.py
        # đã chặn nội dung quá ngắn, nhưng vẫn giữ nhánh dự phòng này để không bao giờ trả 0 section.
        stripped = markdown.strip()
        drafts = [SectionDraft(0, None, stripped, count_tokens(stripped))]
    return drafts


def split_into_chunks(section: SectionDraft) -> list[ChunkDraft]:
    """Cắt nội dung một section thành các chunk ~256 từ theo ranh giới đoạn văn; đoạn nào tự nó đã
    dài hơn mục tiêu (ví dụ bảng lớn) thì cắt cưỡng bức theo từ (mục 11.3). Không bao giờ trả 0 chunk.
    """
    paragraphs = [p for p in re.split(r"\n\s*\n", section.content) if p.strip()]
    if not paragraphs:
        paragraphs = [section.content] if section.content.strip() else []

    groups: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for paragraph in paragraphs:
        paragraph_tokens = count_tokens(paragraph)
        if paragraph_tokens > CHUNK_TARGET_TOKENS:
            if current:
                groups.append("\n\n".join(current))
                current, current_tokens = [], 0
            words = paragraph.split()
            for start in range(0, len(words), CHUNK_TARGET_TOKENS):
                groups.append(" ".join(words[start : start + CHUNK_TARGET_TOKENS]))
            continue
        if current and current_tokens + paragraph_tokens > CHUNK_TARGET_TOKENS:
            groups.append("\n\n".join(current))
            current, current_tokens = [], 0
        current.append(paragraph)
        current_tokens += paragraph_tokens
    if current:
        groups.append("\n\n".join(current))

    if not groups:
        # Section rỗng hoặc chỉ có heading (mục 11.3): một chunk duy nhất giữ nội dung/heading, không bỏ mất.
        fallback = section.content.strip() or (section.heading or "").strip()
        groups = [fallback] if fallback else []

    chunks = [
        ChunkDraft(section.section_index, section.heading, group.strip(), count_tokens(group))
        for group in groups
        if group.strip()
    ]
    if not chunks:
        # Trường hợp cực đoan cuối cùng (section thật sự rỗng) — vẫn không được trả 0 chunk theo mục 11.3.
        chunks = [ChunkDraft(section.section_index, section.heading, "(rỗng)", 1)]
    return chunks
