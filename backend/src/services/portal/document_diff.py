"""So sánh hai phiên bản tài liệu để hiện "So với bản trước" (chỉ đọc, chỉ để hiển thị, không ảnh hưởng dữ liệu hay vector).

Cách làm: cắt Markdown của hai bản thành mục theo đúng luật cắt khi kích hoạt, ghép hai danh sách mục bằng `difflib` theo khóa
(tiêu đề, mã băm nội dung) để nhận ra mục thêm, xóa, sửa kể cả khi mục dịch chỗ, rồi so từng từ bên trong mục đã sửa.
Chỉ so **chữ** (qua Markdown), không so định dạng Word.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document_version import DocumentVersion
from src.services.ingest.chunker import SectionDraft, split_into_sections
from src.services.ingest.ingest_service import chunk_markdown
from src.services.ingest.version_lifecycle import embedding_text_of
from src.services.portal.errors import PortalError

SectionStatus = Literal["added", "removed", "modified", "unchanged"]
SegmentOp = Literal["equal", "insert", "delete"]

# Mục đổi tiêu đề nhưng nội dung còn giống từng này thì coi là "đã sửa" (đổi tên), không phải xóa rồi thêm.
RENAME_SIMILARITY = 0.6
# Mục quá dài thì so từ-theo-từ rất chậm: coi như thay hoàn toàn (hiện cả khối cũ và mới).
MAX_WORD_DIFF_TOKENS = 20_000
# Tốc độ đo thật khi tính embedding trên máy chủ production (khoảng 0,56 giây mỗi đoạn); chỉ để báo trước.
ESTIMATED_SECONDS_PER_CHUNK = 0.6
_TOKEN = re.compile(r"\s+|\S+")


@dataclass(frozen=True)
class Segment:
    op: SegmentOp
    text: str


@dataclass(frozen=True)
class SectionChange:
    status: SectionStatus
    heading: str | None
    old_heading: str | None = None
    segments: list[Segment] = field(default_factory=list)
    added_words: int = 0
    removed_words: int = 0


@dataclass(frozen=True)
class RecomputeEstimate:
    chunks_total: int
    chunks_reused: int
    chunks_to_embed: int
    estimated_seconds: int


@dataclass(frozen=True)
class VersionDiff:
    sections: list[SectionChange]
    added: int
    removed: int
    modified: int
    unchanged: int
    recompute: RecomputeEstimate


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _key(section: SectionDraft) -> tuple[str, str]:
    return (section.heading or "", _hash(section.content))


def _words(text: str) -> int:
    return len(text.split())


def word_diff(old: str, new: str) -> list[Segment]:
    """So khớp theo từ (giữ cả khoảng trắng để ghép lại đúng văn bản). Khoảng trắng đứng giữa hai chỗ đổi được gộp vào
    chỗ đổi để mỗi cụm từ thay thế hiện thành một khối xóa và một khối thêm, không vụn từng chữ."""
    a, b = _TOKEN.findall(old), _TOKEN.findall(new)
    if len(a) + len(b) > MAX_WORD_DIFF_TOKENS:
        return [Segment("delete", old), Segment("insert", new)]
    # Mỗi khối: (có đổi không, văn bản cũ, văn bản mới).
    blocks: list[tuple[bool, str, str]] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        blocks.append((tag != "equal", "".join(a[i1:i2]), "".join(b[j1:j2])))
    merged: list[tuple[bool, str, str]] = []
    for index, (changed, before, after) in enumerate(blocks):
        is_gap = (
            not changed
            and before.isspace()
            and merged
            and merged[-1][0]
            and index + 1 < len(blocks)
            and blocks[index + 1][0]
        )
        if (changed or is_gap) and merged and merged[-1][0]:
            _, prev_before, prev_after = merged[-1]
            merged[-1] = (True, prev_before + before, prev_after + after)
        else:
            merged.append((changed, before, after))
    segments: list[Segment] = []
    for changed, before, after in merged:
        if not changed:
            segments.append(Segment("equal", before))
            continue
        if before:
            segments.append(Segment("delete", before))
        if after:
            segments.append(Segment("insert", after))
    return segments


def _modified(old: SectionDraft, new: SectionDraft) -> SectionChange:
    segments = word_diff(old.content, new.content)
    return SectionChange(
        status="modified",
        heading=new.heading,
        old_heading=old.heading if old.heading != new.heading else None,
        segments=segments,
        added_words=sum(_words(s.text) for s in segments if s.op == "insert"),
        removed_words=sum(_words(s.text) for s in segments if s.op == "delete"),
    )


def _pair_block(olds: list[SectionDraft], news: list[SectionDraft]) -> list[SectionChange]:
    """Trong một khối khác nhau: ghép mục cũ với mới cùng tiêu đề, rồi theo độ giống nội dung; còn lại là xóa hoặc thêm."""
    pair_of: dict[int, int] = {}  # chỉ số mục mới -> chỉ số mục cũ
    used_old: set[int] = set()
    for j, new in enumerate(news):
        for i, old in enumerate(olds):
            if i not in used_old and old.heading == new.heading and new.heading:
                pair_of[j] = i
                used_old.add(i)
                break
    for j, new in enumerate(news):
        if j in pair_of:
            continue
        best, best_ratio = None, RENAME_SIMILARITY
        for i, old in enumerate(olds):
            if i in used_old:
                continue
            matcher = SequenceMatcher(None, old.content, new.content, autojunk=False)
            if matcher.real_quick_ratio() >= best_ratio and matcher.quick_ratio() >= best_ratio:
                ratio = matcher.ratio()
                if ratio >= best_ratio:
                    best, best_ratio = i, ratio
        if best is not None:
            pair_of[j] = best
            used_old.add(best)

    changes = [
        SectionChange(
            status="removed",
            heading=old.heading,
            segments=[Segment("delete", old.content)],
            removed_words=_words(old.content),
        )
        for i, old in enumerate(olds)
        if i not in used_old
    ]
    for j, new in enumerate(news):
        if j in pair_of:
            changes.append(_modified(olds[pair_of[j]], new))
        else:
            changes.append(
                SectionChange(
                    status="added",
                    heading=new.heading,
                    segments=[Segment("insert", new.content)],
                    added_words=_words(new.content),
                )
            )
    return changes


def _estimate(old_markdown: str, new_markdown: str) -> RecomputeEstimate:
    """Số đoạn của bản mới chưa có vector khi chỉ xét bản so sánh (bản thật còn tra được các bản khác nên có thể ít hơn)."""
    _, old_chunks = chunk_markdown(old_markdown)
    _, new_chunks = chunk_markdown(new_markdown)
    known = {embedding_text_of(chunk) for chunk in old_chunks}
    texts = [embedding_text_of(chunk) for chunk in new_chunks]
    to_embed = len({text for text in texts if text not in known})
    return RecomputeEstimate(
        chunks_total=len(texts),
        chunks_reused=sum(1 for text in texts if text in known),
        chunks_to_embed=to_embed,
        estimated_seconds=round(to_embed * ESTIMATED_SECONDS_PER_CHUNK),
    )


def diff_markdown(old_markdown: str, new_markdown: str) -> VersionDiff:
    old_sections = split_into_sections(old_markdown)
    new_sections = split_into_sections(new_markdown)
    changes: list[SectionChange] = []
    matcher = SequenceMatcher(None, [_key(s) for s in old_sections], [_key(s) for s in new_sections], autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            changes.extend(SectionChange(status="unchanged", heading=s.heading) for s in new_sections[j1:j2])
        else:
            changes.extend(_pair_block(old_sections[i1:i2], new_sections[j1:j2]))
    counts = {
        status: sum(1 for c in changes if c.status == status)
        for status in ("added", "removed", "modified", "unchanged")
    }
    return VersionDiff(
        sections=changes,
        added=counts["added"],
        removed=counts["removed"],
        modified=counts["modified"],
        unchanged=counts["unchanged"],
        recompute=_estimate(old_markdown, new_markdown),
    )


@dataclass(frozen=True)
class VersionComparison:
    base_version_id: int | None
    base_version_label: str | None
    base_reason: Literal["requested", "parent", "previous_revision"] | None
    diff: VersionDiff | None


async def compare_with_base(
    session: AsyncSession, *, document_id: int, version_id: int, base_version_id: int | None = None
) -> VersionComparison:
    """So `version_id` với bản nền: bản được chỉ định, nếu không thì bản cha (`parent_version_id`), nếu không thì bản
    ngay trước theo số thứ tự. Tài liệu chưa có bản nào trước đó: `diff=None` (hiện "tài liệu mới")."""
    version = await session.get(DocumentVersion, version_id)
    if version is None or version.document_id != document_id:
        raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
    base: DocumentVersion | None = None
    reason: Literal["requested", "parent", "previous_revision"] | None = None
    if base_version_id is not None:
        base = await session.get(DocumentVersion, base_version_id)
        if base is None or base.document_id != document_id or base.id == version.id:
            raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
        reason = "requested"
    elif version.parent_version_id is not None:
        base = await session.get(DocumentVersion, version.parent_version_id)
        reason = "parent"
    if base is None:
        base = await session.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id, DocumentVersion.revision_no < version.revision_no)
            .order_by(DocumentVersion.revision_no.desc())
            .limit(1)
        )
        reason = "previous_revision" if base is not None else None
    if base is None:
        return VersionComparison(None, None, None, None)
    diff = await asyncio.to_thread(diff_markdown, base.markdown, version.markdown)
    return VersionComparison(base.id, base.version_label, reason, diff)
