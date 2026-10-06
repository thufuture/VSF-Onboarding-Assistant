"""Chia cấu trúc tài liệu khi file thiếu heading (mục 13 của plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md).

Nguyên tắc: **rule-based trước, AI là phương án cuối; không bao giờ đổi chữ của tài liệu** (chỉ quyết định cắt ở đâu và
đặt tên gì), nên kiểm chứng trích dẫn nguyên văn (INV6/INV13) luôn còn đúng.

- Bậc 2 (`infer_headings`): file KHÔNG có heading thật thì nhận "tiêu đề giả" (dòng ngắn chỉ in đậm, dòng đánh số,
  dòng toàn chữ hoa đứng riêng) và thăng thành heading. Cùng đầu vào luôn ra cùng kết quả.
- Bậc 3 (`analyze_structure`): đo chất lượng cấu trúc (GOOD / MEDIUM / POOR) và sinh cảnh báo cho HR.
- Bậc 1 (`subdivide_sections`): section dài quá ngưỡng thì cắt tiếp theo ranh giới đoạn thành section phụ.
- Bậc 5 (`ai_split_markdown`): LLM chỉ ra đoạn nào là tiêu đề; mọi đề xuất đều bị kiểm bằng code, sai thì bỏ hết.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.services.ingest.chunker import SectionDraft, count_tokens, split_into_sections

_REAL_HEADING_RE = re.compile(r"^#{1,3}\s+\S")
_BOLD_LINE_RE = re.compile(r"^(?:\*\*|__)\s*(.{2,100}?)\s*(?:\*\*|__)\s*[:：]?\s*$")
_NUMBERED_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2})[.)]?\s+(\S.{1,90})$")
_TRAILING_SENTENCE_END = (".", ";", ",", "?", "!")

MIN_INFERRED_HEADINGS = 2
MAX_TITLE_CHARS = 100
# Section dài hơn ngưỡng này (theo số từ) thì cắt thành section phụ; ngưỡng chốt cảm tính ở giai đoạn đầu và
# sẽ chỉnh theo số đo thật (mục 13.7 câu 2).
SECTION_MAX_WORDS = 800
SUBSECTION_TARGET_WORDS = 400
# Văn bản ngắn thì một section là đủ, không coi là "kém cấu trúc".
POOR_MIN_WORDS = 300

Quality = Literal["GOOD", "MEDIUM", "POOR"]
Method = Literal["HEADINGS", "INFERRED", "NONE"]

WARNING_NO_STRUCTURE = "NO_STRUCTURE"
WARNING_LONG_SECTIONS = "LONG_SECTIONS_SPLIT"
WARNING_INFERRED = "HEADINGS_INFERRED"


@dataclass(frozen=True)
class StructureReport:
    quality: Quality
    method: Method
    heading_count: int
    section_count: int
    word_count: int
    max_section_words: int
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "quality": self.quality,
            "method": self.method,
            "heading_count": self.heading_count,
            "section_count": self.section_count,
            "word_count": self.word_count,
            "max_section_words": self.max_section_words,
            "warnings": list(self.warnings),
        }


def count_real_headings(markdown: str) -> int:
    in_code = False
    count = 0
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        elif not in_code and _REAL_HEADING_RE.match(line):
            count += 1
    return count


def _is_caps_title(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    if len(letters) < 4 or len(line) > 80 or line.endswith(_TRAILING_SENTENCE_END):
        return False
    return sum(1 for c in letters if c.isupper()) / len(letters) >= 0.9


def _candidate(line: str, prev_blank: bool, next_blank: bool) -> tuple[str, str] | None:
    """Trả (mức heading `##`/`###`, tiêu đề) nếu dòng trông như tiêu đề giả, ngược lại None."""
    stripped = line.strip()
    if not stripped or stripped.startswith(("|", "- ", "* ", "+ ", ">", "#")):
        return None
    title = stripped
    bold = _BOLD_LINE_RE.match(stripped)
    if bold:
        title = bold.group(1).strip()
    numbered = _NUMBERED_RE.match(title)
    if numbered and not title.endswith(_TRAILING_SENTENCE_END):
        # "1. Hồ sơ" là tiêu đề, "1. Mang theo CCCD." là một bước trong danh sách; câu có dấu kết thúc bị loại.
        level = "##" if "." not in numbered.group(1) else "###"
        return level, title
    if bold and not title.endswith(_TRAILING_SENTENCE_END):
        return "##", title
    if prev_blank and next_blank and _is_caps_title(stripped):
        return "##", stripped
    return None


def infer_headings(markdown: str) -> tuple[str, int]:
    """Bậc 2: thăng tiêu đề giả thành heading. Chỉ gọi khi file không có heading thật.

    Trả (markdown mới, số tiêu đề nhận được). Nhận được ít hơn `MIN_INFERRED_HEADINGS` thì trả nguyên văn bản gốc.
    """
    lines = markdown.splitlines()
    in_code = False
    found: dict[int, tuple[str, str]] = {}
    for index, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        prev_blank = index == 0 or not lines[index - 1].strip()
        next_blank = index == len(lines) - 1 or not lines[index + 1].strip()
        result = _candidate(line, prev_blank, next_blank)
        if result is not None:
            found[index] = result

    # Hai dòng ứng viên liền nhau là danh sách ngắn chứ không phải tiêu đề + nội dung: bỏ các dòng đó.
    def next_text_index(start: int) -> int | None:
        for j in range(start + 1, len(lines)):
            if lines[j].strip():
                return j
        return None

    cleaned = {index: value for index, value in found.items() if (next_text_index(index) not in found)}
    if len(cleaned) < MIN_INFERRED_HEADINGS:
        return markdown, 0
    out = list(lines)
    for index, (level, title) in cleaned.items():
        out[index] = f"{level} {title[:MAX_TITLE_CHARS]}"
    return "\n".join(out) + ("\n" if markdown.endswith("\n") else ""), len(cleaned)


def _section_stats(markdown: str) -> tuple[int, int]:
    sections = split_into_sections(markdown)
    return len(sections), max((section.token_count for section in sections), default=0)


def analyze_structure(markdown: str, *, infer: bool = True) -> tuple[str, StructureReport]:
    """Bậc 2 + 3: trả (markdown đã thăng tiêu đề giả nếu cần, báo cáo chất lượng cấu trúc).

    `infer=False` chỉ đo, không đổi chữ (dùng khi HR đã sửa tay bản nháp: không tự thăng lại tiêu đề họ đã bỏ).
    """
    word_count = count_tokens(markdown)
    warnings: list[str] = []
    method: Method
    real = count_real_headings(markdown)
    text = markdown
    if real > 0:
        method = "HEADINGS"
        heading_count = real
    else:
        inferred = 0
        if infer:
            text, inferred = infer_headings(markdown)
        if inferred:
            method = "INFERRED"
            heading_count = inferred
            warnings.append(WARNING_INFERRED)
        else:
            method = "NONE"
            heading_count = 0

    section_count, max_words = _section_stats(text)
    if max_words > SECTION_MAX_WORDS:
        warnings.append(WARNING_LONG_SECTIONS)
    quality: Quality
    if method == "NONE" and word_count >= POOR_MIN_WORDS:
        quality = "POOR"
        warnings.append(WARNING_NO_STRUCTURE)
    elif method == "INFERRED" or max_words > SECTION_MAX_WORDS:
        quality = "MEDIUM"
    else:
        quality = "GOOD"
    return text, StructureReport(
        quality=quality,
        method=method,
        heading_count=heading_count,
        section_count=section_count,
        word_count=word_count,
        max_section_words=max_words,
        warnings=warnings,
    )


def _paragraph_groups(content: str) -> list[str]:
    """Tách nội dung thành các khối theo đoạn văn; khối quá dài và không có dòng trống thì tách tiếp theo dòng."""
    blocks = [block for block in re.split(r"\n\s*\n", content) if block.strip()]
    pieces: list[str] = []
    for block in blocks:
        if count_tokens(block) <= SUBSECTION_TARGET_WORDS:
            pieces.append(block)
            continue
        pieces.extend(line for line in block.split("\n") if line.strip())
    return pieces


def subdivide_sections(sections: list[SectionDraft]) -> list[SectionDraft]:
    """Bậc 1: cắt section dài hơn `SECTION_MAX_WORDS` thành section phụ ~`SUBSECTION_TARGET_WORDS` từ.

    Tên section phụ: "<tiêu đề> (phần N)" hoặc "Phần N" nếu không có tiêu đề. Chỉ cắt ở ranh giới đoạn/dòng.
    """
    result: list[SectionDraft] = []
    for section in sections:
        if section.token_count <= SECTION_MAX_WORDS:
            result.append(section)
            continue
        groups: list[list[str]] = []
        current: list[str] = []
        current_words = 0
        for piece in _paragraph_groups(section.content):
            words = count_tokens(piece)
            if current and current_words + words > SUBSECTION_TARGET_WORDS:
                groups.append(current)
                current, current_words = [], 0
            current.append(piece)
            current_words += words
        if current:
            groups.append(current)
        if len(groups) <= 1:
            result.append(section)
            continue
        for number, group in enumerate(groups, start=1):
            content = "\n\n".join(group).strip()
            heading = f"{section.heading} (phần {number})" if section.heading else f"Phần {number}"
            result.append(SectionDraft(0, heading, content, count_tokens(content)))
    return [SectionDraft(index, s.heading, s.content, s.token_count) for index, s in enumerate(result)]


# --- Bậc 5: LLM chỉ ra tiêu đề nằm ở đâu ---

AI_MAX_PARAGRAPHS = 400
AI_PARAGRAPH_PREVIEW_CHARS = 160
AI_MAX_HEADINGS = 40

AI_SYSTEM_PROMPT = (
    "Bạn giúp chia một tài liệu nội bộ chưa có tiêu đề thành các mục. Tài liệu được đánh số theo đoạn (§1, §2, ...), mỗi "
    "đoạn có thể bị cắt ngắn. Hãy chỉ ra đoạn nào là ĐẦU của một mục mới. Tuyệt đối không viết lại hay sửa nội dung. "
    'Trả về JSON đúng dạng {"headings": [{"paragraph": số_đoạn, "level": 1|2|3, "title": "tên ngắn của mục"}]}. '
    "Số đoạn phải tăng dần, không trùng. Chỉ dùng số đoạn đã cho."
)


@dataclass(frozen=True)
class AiHeading:
    paragraph: int  # chỉ số dòng (đã đánh số từ 1) trong danh sách đoạn gửi cho LLM
    level: int
    title: str


@dataclass(frozen=True)
class AiSplit:
    markdown: str
    headings: list[AiHeading]


def numbered_paragraphs(markdown: str) -> list[tuple[int, str]]:
    """Các dòng có chữ, kèm chỉ số dòng trong `markdown.splitlines()` (đoạn số N = phần tử thứ N-1 của danh sách)."""
    return [(index, line) for index, line in enumerate(markdown.splitlines()) if line.strip()]


def build_ai_prompt(paragraphs: list[tuple[int, str]]) -> str:
    rows = []
    for number, (_, line) in enumerate(paragraphs, start=1):
        text = line.strip()
        if len(text) > AI_PARAGRAPH_PREVIEW_CHARS:
            text = text[:AI_PARAGRAPH_PREVIEW_CHARS] + "…"
        rows.append(f"§{number} {text}")
    return "\n".join(rows)


def validate_ai_headings(raw: str, paragraph_count: int) -> list[AiHeading] | None:
    """Kiểm đề xuất của LLM bằng code. Trả None nếu có bất kỳ điều gì không hợp lệ (bỏ hết, giữ rule-based)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    items = data.get("headings") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None
    headings: list[AiHeading] = []
    previous = 0
    for item in items:
        if not isinstance(item, dict):
            return None
        paragraph, level, title = item.get("paragraph"), item.get("level"), item.get("title")
        if not isinstance(paragraph, int) or isinstance(paragraph, bool) or not 1 <= paragraph <= paragraph_count:
            return None
        if paragraph <= previous:  # không trùng, phải tăng dần
            return None
        if not isinstance(level, int) or isinstance(level, bool) or level not in (1, 2, 3):
            return None
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE_CHARS:
            return None
        previous = paragraph
        headings.append(AiHeading(paragraph, level, " ".join(title.split())))
    limit = min(AI_MAX_HEADINGS, max(MIN_INFERRED_HEADINGS, paragraph_count // 2))
    if not MIN_INFERRED_HEADINGS <= len(headings) <= limit:
        return None
    return headings


def apply_ai_headings(markdown: str, paragraphs: list[tuple[int, str]], headings: list[AiHeading]) -> AiSplit | None:
    """Chèn dòng heading trước đoạn được chỉ; kiểm chữ gốc không đổi (bỏ dòng heading đã chèn thì phải y hệt bản đầu)."""
    lines = markdown.splitlines()
    insert_before: dict[int, AiHeading] = {paragraphs[h.paragraph - 1][0]: h for h in headings}
    out: list[str] = []
    inserted: set[int] = set()
    for index, line in enumerate(lines):
        heading = insert_before.get(index)
        if heading is not None:
            inserted.add(len(out))
            out.append(f"{'#' * heading.level} {heading.title}")
        out.append(line)
    original_again = [line for i, line in enumerate(out) if i not in inserted]
    if original_again != lines:
        return None
    text = "\n".join(out) + ("\n" if markdown.endswith("\n") else "")
    return AiSplit(markdown=text, headings=headings)


async def ai_split_markdown(markdown: str, llm: ChatCompletionPort) -> AiSplit | None:
    """Bậc 5: nhờ LLM chỉ ra tiêu đề. Mọi lỗi (mạng, JSON, kiểm chứng) đều trả None để nạp tiếp bằng kết quả rule-based."""
    paragraphs = numbered_paragraphs(markdown)
    if len(paragraphs) < 2 * MIN_INFERRED_HEADINGS or len(paragraphs) > AI_MAX_PARAGRAPHS:
        return None
    try:
        raw = await llm.complete_json(system_prompt=AI_SYSTEM_PROMPT, user_prompt=build_ai_prompt(paragraphs))
    except Exception:
        return None
    headings = validate_ai_headings(raw, len(paragraphs))
    if headings is None:
        return None
    return apply_ai_headings(markdown, paragraphs, headings)
