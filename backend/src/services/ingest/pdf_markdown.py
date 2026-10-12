"""Đọc PDF có lớp chữ thành Markdown có cấu trúc: tiêu đề (theo cỡ chữ và độ đậm), đoạn văn, danh sách.

Bộ đọc mặc định (markitdown -> pdfminer) trả chữ phẳng nên PDF xuất từ Word mất hết tiêu đề (đo thật: Word 18 mục, PDF 3 mục) và PDF đã OCR
thành một dòng duy nhất (1 mục). Ở đây dùng chính pdfminer.six nhưng giữ thông tin từng dòng (cỡ chữ, font đậm, vị trí):

- Cỡ chữ thân bài là cỡ phổ biến nhất của tài liệu. Dòng lớn hơn rõ rệt, hoặc cả khối ngắn in đậm hoàn toàn, là tiêu đề; cấp tiêu đề
  xếp theo cỡ chữ lớn đến nhỏ.
- Tiêu đề và số trang lặp lại ở đầu/cuối mỗi trang bị bỏ.
- Mỗi khối chữ mà pdfminer gom theo khoảng cách dòng là một đoạn; các dòng trong khối được nối lại.

Chỉ dùng khi bật `PDF_STRUCTURE_ENABLED`; lỗi hoặc kết quả quá ít chữ thì bộ gọi quay về bộ đọc cũ.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTChar, LTFigure, LTTextContainer, LTTextLine

MAX_HEADING_LEVEL = 4
SIZE_HEADING_RATIO = 1.12  # lớn hơn cỡ thân bài chừng này thì là tiêu đề
BOLD_HEADING_MAX_CHARS = 160  # khối in đậm hoàn toàn dài hơn thế là đoạn nhấn mạnh, không phải tiêu đề
BOLD_HEADING_MAX_LINES = 3
EDGE_ZONE = 0.08  # vùng đầu/cuối trang (tỉ lệ chiều cao) tìm tiêu đề trang lặp lại

_BULLET_CHARS = "•·▪◦●○■□‣⁃"
_PRIVATE_USE = f"{chr(0xE000)}-{chr(0xF8FF)}"  # k\u00fd hi\u1ec7u \u0111\u1ea7u d\u00f2ng c\u1ee7a font Symbol/Wingdings \u0111\u01b0\u1ee3c PDF/Word ghi \u1edf v\u00f9ng k\u00fd t\u1ef1 ri\u00eang
_BULLET = re.compile(rf"^\s*(?:[{_BULLET_CHARS}{_PRIVATE_USE}]\s*|[-\u2013oO]\s+)(?=\S)")
_BULLET_ONLY = re.compile(rf"^\s*(?:[{_BULLET_CHARS}{_PRIVATE_USE}]|-)\s*$")
_LEADING_SYMBOL = re.compile(rf"^([ \t]*)[{_PRIVATE_USE}][ \t]*", re.MULTILINE)
_ANY_SYMBOL = re.compile(f"[{_PRIVATE_USE}]")


def normalize_symbol_bullets(markdown: str) -> str:
    """Markdown \u0111\u1ecdc t\u1eeb Word c\u00f3 th\u1ec3 gi\u1eef nguy\u00ean k\u00fd hi\u1ec7u \u0111\u1ea7u d\u00f2ng c\u1ee7a font Symbol (k\u00fd t\u1ef1 v\u00f9ng ri\u00eang, hi\u1ec7n th\u00e0nh \u00f4 vu\u00f4ng); \u0111\u1ed5i v\u1ec1 `- `."""
    return _ANY_SYMBOL.sub("", _LEADING_SYMBOL.sub(r"\1- ", markdown))


_DIGITS = re.compile(r"\d+")
_BOLD_NAME = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)


@dataclass
class _Line:
    text: str
    size: float
    bold: bool
    x0: float
    x1: float
    y0: float
    y1: float
    y_ratio: float  # 0 = đáy trang, 1 = đỉnh trang
    box: int
    page: int


@dataclass
class _Block:
    lines: list[_Line] = field(default_factory=list)


def _line_of(element: LTTextLine, page_height: float, box: int, page: int) -> _Line | None:
    chars = [c for c in element if isinstance(c, LTChar) and not c.get_text().isspace()]
    text = element.get_text().replace("\n", " ").strip()
    if not chars or not text:
        return None
    sizes = [round(c.size, 1) for c in chars]
    bold_chars = sum(1 for c in chars if _BOLD_NAME.search(c.fontname or ""))
    return _Line(
        text=re.sub(r"\s+", " ", text),
        size=statistics.median(sizes),
        bold=bold_chars / len(chars) >= 0.85,
        x0=element.x0,
        x1=element.x1,
        y0=element.y0,
        y1=element.y1,
        y_ratio=(element.y0 + element.y1) / 2 / page_height if page_height else 0.5,
        box=box,
        page=page,
    )


def _text_containers(container: Iterable[object]) -> Iterator[LTTextContainer[Any]]:
    """Các khối chữ theo thứ tự đọc của pdfminer, đi sâu vào hình/khung chứa chữ."""
    for element in container:
        if isinstance(element, LTTextContainer):
            yield element
        elif isinstance(element, LTFigure):
            yield from _text_containers(element)


def _read_pages(path: Path) -> list[list[_Line]]:
    pages: list[list[_Line]] = []
    params = LAParams(
        line_margin=0.3, boxes_flow=0.5, all_texts=True
    )  # all_texts: chữ nằm trong hình/khung (form XObject) cũng được đọc
    for number, layout in enumerate(extract_pages(str(path), laparams=params)):
        lines: list[_Line] = []
        for box, element in enumerate(_text_containers(layout)):
            for line in element:
                if isinstance(line, LTTextLine):
                    item = _line_of(line, layout.height, number * 10_000 + box, number)
                    if item:
                        lines.append(item)
        pages.append(lines)
    return pages


def _join_lone_bullets(page: list[_Line]) -> list[_Line]:
    """pdfminer hay tách ký hiệu đầu dòng (font Symbol) thành một dòng riêng cùng độ cao với chữ; ghép lại thành "• chữ"."""
    lone = [line for line in page if _BULLET_ONLY.match(line.text)]
    if not lone:
        return page
    drop: set[int] = set()
    for bullet in lone:
        partners = [
            line
            for line in page
            if line is not bullet
            and id(line) not in drop
            and not _BULLET_ONLY.match(line.text)
            and line.x0 > bullet.x0
            and abs((line.y0 + line.y1) / 2 - (bullet.y0 + bullet.y1) / 2) <= max(2.0, bullet.size * 0.4)
        ]
        drop.add(id(bullet))
        if partners:
            partner = min(partners, key=lambda line: line.x0)
            if not _BULLET.match(partner.text):
                partner.text = "• " + partner.text
                partner.x0 = bullet.x0
    return [line for line in page if id(line) not in drop]


def _drop_page_furniture(pages: list[list[_Line]]) -> list[list[_Line]]:
    """Bỏ số trang và tiêu đề/chân trang lặp lại (chuẩn hóa bằng cách bỏ chữ số) ở vùng sát mép trang."""
    if len(pages) < 3:
        return [[line for line in page if not _is_page_number(line, edge=True)] for page in pages]
    seen: Counter[str] = Counter()
    for page in pages:
        keys = {_DIGITS.sub("#", line.text) for line in page if _in_edge(line)}
        seen.update(keys)
    threshold = max(3, len(pages) // 2)
    repeated = {key for key, count in seen.items() if count >= threshold}
    return [
        [
            line
            for line in page
            if not (_in_edge(line) and (_DIGITS.sub("#", line.text) in repeated or _is_page_number(line)))
        ]
        for page in pages
    ]


def _in_edge(line: _Line) -> bool:
    return line.y_ratio >= 1 - EDGE_ZONE or line.y_ratio <= EDGE_ZONE


def _is_page_number(line: _Line, *, edge: bool = False) -> bool:
    return (not edge or _in_edge(line)) and bool(
        re.fullmatch(r"(?:trang\s*)?\d{1,4}(?:\s*/\s*\d{1,4})?", line.text.strip(), re.IGNORECASE)
    )


def _body_size(pages: list[list[_Line]]) -> float:
    weight: Counter[float] = Counter()
    for page in pages:
        for line in page:
            weight[round(line.size * 2) / 2] += len(line.text)
    return weight.most_common(1)[0][0] if weight else 0.0


def _blocks(page: list[_Line]) -> list[_Block]:
    ordered: dict[int, _Block] = {}
    for line in page:
        ordered.setdefault(line.box, _Block()).lines.append(line)
    return list(ordered.values())


def pdf_to_markdown(path: Path) -> str:
    """Trả Markdown có tiêu đề `#`; rỗng nếu PDF không có lớp chữ. Có thể ném lỗi của pdfminer khi PDF hỏng."""
    pages = _drop_page_furniture([_join_lone_bullets(page) for page in _read_pages(path)])
    body = _body_size(pages)
    if body <= 0:
        return ""

    def is_heading_block(block: _Block) -> bool:
        lines = block.lines
        size = max(line.size for line in lines)
        if size >= body * SIZE_HEADING_RATIO and sum(len(line.text) for line in lines) <= 240:
            return True
        return (
            all(line.bold for line in lines)
            and len(lines) <= BOLD_HEADING_MAX_LINES
            and sum(len(line.text) for line in lines) <= BOLD_HEADING_MAX_CHARS
            and not _BULLET.match(lines[0].text)
            and not lines[0].text[:1].islower()  # đuôi của dòng in đậm bị xuống dòng (ví dụ phần cuối một đường link)
        )

    def style_of(block: _Block) -> tuple[float, bool]:
        return round(max(line.size for line in block.lines)), all(line.bold for line in block.lines)

    def page_blocks(page: list[_Line]) -> list[_Block]:
        """Các dòng tiêu đề liền nhau cùng kiểu (một tiêu đề xuống dòng) gộp thành một khối."""
        merged: list[_Block] = []
        for block in _blocks(page):
            last = merged[-1] if merged else None
            if (
                last is not None
                and is_heading_block(last)
                and is_heading_block(block)
                and style_of(last) == style_of(block)
                and 0 <= last.lines[-1].y0 - block.lines[0].y1 <= last.lines[-1].size * 0.6
            ):
                last.lines.extend(block.lines)
            else:
                merged.append(block)
        return merged

    # cấp tiêu đề: xếp các "kiểu" (cỡ làm tròn, đậm) từ lớn đến nhỏ
    styles = {style_of(block) for page in pages for block in page_blocks(page) if is_heading_block(block)}
    ranked = sorted(styles, reverse=True)
    level_of = {style: min(index + 1, MAX_HEADING_LEVEL) for index, style in enumerate(ranked)}

    out: list[str] = []
    previous_was_bullet = False
    for page in pages:
        for block in page_blocks(page):
            if is_heading_block(block):
                key = (round(max(line.size for line in block.lines)), all(line.bold for line in block.lines))
                out.append("")
                out.append(f"{'#' * level_of[key]} {' '.join(line.text for line in block.lines)}")
                out.append("")
                previous_was_bullet = False
                continue
            paragraph = ""
            for line in block.lines:
                bullet = _BULLET.match(line.text)
                if bullet:
                    if paragraph:
                        out.extend(["", paragraph, ""])
                        paragraph = ""
                    if not previous_was_bullet and out and out[-1] != "":
                        out.append("")
                    indent = "  " if line.x0 > min(item.x0 for item in block.lines) + 6 else ""
                    out.append(f"{indent}- " + line.text[bullet.end() :].strip())
                    previous_was_bullet = True
                    continue
                if (
                    previous_was_bullet
                    and out
                    and out[-1].startswith("- ")
                    and line.x0 > block.lines[0].x0 + 2
                    and not paragraph
                ):
                    out[-1] += " " + line.text  # dòng gập của mục danh sách
                    continue
                previous_was_bullet = False
                paragraph = f"{paragraph} {line.text}".strip() if paragraph else line.text
            if paragraph:
                out.extend(["", paragraph, ""])
                previous_was_bullet = False
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
