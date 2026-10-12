"""Vá thay đổi của HR vào Markdown gốc mà KHÔNG đụng phần không sửa.

Bài toán: với bản nháp từ PDF, Markdown `M` được đọc thẳng từ PDF (đã chunk, đã embedding). Để sửa, HR dùng bản Word dựng lại từ PDF.
Nếu lưu xong lại đọc cả bản Word thành Markdown mới thì mọi chỗ ngắt dòng khác đi, mọi đoạn đều bị coi là "đã đổi" và phải tính lại
embedding. Cách làm ở đây:

- `B0`: Markdown đọc từ bản Word ngay sau khi chuyển (trước khi HR sửa). `B1`: Markdown đọc từ bản Word sau khi HR sửa.
  B0 và B1 đọc bằng **cùng một bộ đọc** nên khác biệt giữa chúng chính là phần HR đã sửa.
- So B0 với B1 theo từng từ để biết đúng chỗ sửa. Với mỗi chỗ sửa, tìm trong M hai "mỏ neo" (chuỗi K từ giống hệt, xuất hiện đúng một lần)
  ở hai bên, rồi thay đoạn giữa hai mỏ neo bằng đoạn tương ứng của B1. Mọi chỗ còn lại của M giữ nguyên từng ký tự.
- Không tìm được mỏ neo đáng tin (chỗ sửa nằm trong văn bản lặp lại, hay B0 và M quá khác nhau) thì báo `ok=False` để người gọi dùng
  nguyên B1 (đúng nhưng mọi đoạn bị coi là đổi).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

ANCHOR = 5  # số từ của một mỏ neo
MAX_SLIDE = 80  # tối đa số từ trượt ra xa chỗ sửa để tìm mỏ neo
MIN_SIMILARITY = 0.985  # sau khi vá, M phải giống B1 đến mức này (theo từ)

_TOKEN = re.compile(r"\S+")
_MARKUP = re.compile(
    "[#*_|>`\\[\\]\\\\•·\ue000-\uf8ff]+"
)  # dấu Markdown và ký hiệu đầu dòng (kể cả ký tự font Symbol của Word)


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    norm: str


@dataclass(frozen=True)
class PatchResult:
    markdown: str
    ok: bool
    changed: bool
    groups: int = 0
    reason: str = ""


def _tokens(text: str) -> list[_Token]:
    result: list[_Token] = []
    for match in _TOKEN.finditer(text):
        norm = _MARKUP.sub("", unicodedata.normalize("NFC", match.group())).strip("-–—")
        if norm:
            result.append(_Token(match.start(), match.end(), norm))
    return result


def _balance(text: str) -> str:
    """Đoạn cắt từ B1 có thể chứa nửa dấu in đậm/nghiêng (`**`, `_`) vì ranh giới cắt giữa hai đoạn; bỏ dấu lẻ để không làm hỏng M."""
    for marker in ("**", "__"):
        if text.count(marker) % 2 == 1:
            text = (
                text.replace(marker, "", 1)
                if text.startswith(marker)
                else text[: text.rfind(marker)] + text[text.rfind(marker) + 2 :]
            )
    return text


def _groups(ops: Sequence[tuple[str, int, int, int, int]]) -> list[list[int]]:
    """Gộp các chỗ sửa gần nhau (cách chưa tới hai mỏ neo) để mỏ neo của chúng không chồng lên nhau."""
    merged: list[list[int]] = []
    for _tag, i1, i2, j1, j2 in ops:
        if merged and i1 - merged[-1][1] < 2 * ANCHOR:
            merged[-1][1], merged[-1][3] = i2, j2
        else:
            merged.append([i1, i2, j1, j2])
    return merged


_EDGES = re.compile(r"^(\W*)(.*?)(\W*)$", re.DOTALL)
MAX_PIECES = 5


def _letters_only(token: str) -> bool:
    return token.isalpha()


def _resegment(text: str, vocabulary: set[str]) -> str:
    """Tách lại các từ bị dính ("chỉdẫn" -> "chỉ dẫn") theo từ vựng của M.

    Hai bộ đọc PDF khác nhau (pdfminer cho M, PyMuPDF trong pdf2docx cho B0/B1) quyết định chỗ có dấu cách khác nhau khi PDF không có ký tự
    dấu cách thật giữa hai từ; nếu không chữa thì M và B0 lệch từng từ và bước vá luôn thất bại. Chỉ tách khi từ dính không có trong M và
    ghép được đúng từ các từ có trong M (tối đa MAX_PIECES), nên văn bản mới HR gõ hầu như không bị đổi."""

    def split(core: str) -> list[str] | None:
        best: list[list[str] | None] = [None] * (len(core) + 1)
        best[0] = []
        for end in range(1, len(core) + 1):
            for start in range(max(0, end - 20), end):
                head = best[start]
                piece = core[start:end]
                if (
                    head is None
                    or len(head) >= MAX_PIECES
                    or (len(piece) < 2 and piece.lower() != "ở")
                    or piece not in vocabulary
                ):
                    continue
                if best[end] is None or len(head) + 1 < len(best[end] or []):
                    best[end] = [*head, piece]
        found = best[len(core)]
        return found if found and len(found) > 1 else None

    def fix(match: re.Match[str]) -> str:
        parts = _EDGES.match(match.group())
        if parts is None:
            return match.group()
        prefix, core, suffix = parts.groups()
        if len(core) < 4 or not _letters_only(core) or unicodedata.normalize("NFC", core) in vocabulary:
            return match.group()
        pieces = split(unicodedata.normalize("NFC", core))
        return f"{prefix}{' '.join(pieces)}{suffix}" if pieces else match.group()

    return _TOKEN.sub(fix, text)


def patch_markdown(m: str, b0: str, b1: str) -> PatchResult:
    tm = _tokens(m)
    vocabulary = {t.norm for t in tm if _letters_only(t.norm)}
    b0, b1 = _resegment(b0, vocabulary), _resegment(b1, vocabulary)
    t0, t1 = _tokens(b0), _tokens(b1)
    n0, n1 = [t.norm for t in t0], [t.norm for t in t1]
    ops = [op for op in SequenceMatcher(None, n0, n1, autojunk=False).get_opcodes() if op[0] != "equal"]
    if not ops:
        return PatchResult(m, ok=True, changed=False)

    nm = [t.norm for t in tm]
    index: dict[tuple[str, ...], list[int]] = {}
    for at in range(len(nm) - ANCHOR + 1):
        index.setdefault(tuple(nm[at : at + ANCHOR]), []).append(at)

    def unique(gram: list[str]) -> int | None:
        found = index.get(tuple(gram), [])
        return found[0] if len(found) == 1 else None

    groups = _groups(ops)
    spans: list[tuple[int, int, str]] = []  # (ký tự bắt đầu trong M, ký tự kết thúc, văn bản thay)
    previous_m_end = 0
    previous_i_end = 0
    for i1, i2, j1, j2 in groups:
        # Mỏ neo trái: ANCHOR từ giống hệt, kết thúc tại e (e <= i1).
        left: tuple[int, int] | None = None
        for e in range(i1, max(previous_i_end, i1 - MAX_SLIDE) - 1, -1):
            if e - ANCHOR < previous_i_end:
                break
            position = unique(n0[e - ANCHOR : e])
            if position is not None and position + ANCHOR >= previous_m_end:
                left = (e, position + ANCHOR)
                break
        if left is None and i1 <= MAX_SLIDE and previous_i_end == 0:
            left = (0, 0)  # chỗ sửa nằm gần đầu tài liệu: neo ở đầu văn bản
        # Mỏ neo phải: ANCHOR từ giống hệt, bắt đầu tại s (s >= i2).
        right: tuple[int, int] | None = None
        if left is not None:
            for s in range(i2, min(len(n0) - ANCHOR, i2 + MAX_SLIDE) + 1):
                position = unique(n0[s : s + ANCHOR])
                if position is not None and position >= left[1]:
                    right = (s, position)
                    break
            if right is None and len(n0) - i2 <= MAX_SLIDE:
                right = (len(n0), len(nm))  # gần cuối tài liệu: neo ở cuối văn bản
        if left is None or right is None:
            return PatchResult(m, ok=False, changed=True, groups=len(groups), reason="không tìm được mỏ neo")
        e, m_left = left
        s, m_right = right
        # Phần B1 tương ứng với B0[e:s] (ngoài chỗ sửa B0 và B1 khớp từng từ, chỉ lệch một hằng số).
        b1_from, b1_to = e + (j1 - i1), s + (j2 - i2)
        if b1_to < b1_from or m_right < m_left:
            return PatchResult(m, ok=False, changed=True, groups=len(groups), reason="mỏ neo đảo thứ tự")
        replacement = _balance(b1[t1[b1_from].start : t1[b1_to - 1].end]) if b1_to > b1_from else ""
        char_start = tm[m_left - 1].end if m_left > 0 else 0
        char_end = tm[m_right].start if m_right < len(tm) else len(m)
        left_gap = m[char_start : tm[m_left].start] if m_left < len(tm) else ""
        right_gap = m[tm[m_right - 1].end : char_end] if m_right > 0 else ""
        spans.append((char_start, char_end, (left_gap or " ") + replacement + (right_gap or " ")))
        previous_m_end, previous_i_end = m_right, s

    patched = m
    for start, end, text in reversed(spans):
        patched = patched[:start] + text + patched[end:]

    ratio = SequenceMatcher(None, [t.norm for t in _tokens(patched)], n1, autojunk=False).ratio()
    if ratio < MIN_SIMILARITY:
        return PatchResult(m, ok=False, changed=True, groups=len(groups), reason=f"độ giống sau khi vá chỉ {ratio:.3f}")
    return PatchResult(patched, ok=True, changed=True, groups=len(groups))
