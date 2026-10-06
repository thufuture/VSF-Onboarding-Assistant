"""AI đề xuất task từ tài liệu đã ingest — P4B mục 8.4/8.5.

Đề xuất KHÔNG được lưu DB cho tới khi HR "accept" (P0A §3: AI chỉ đề xuất, HR quyết). Mọi source_chunk
phải thuộc đúng document_version đã chọn và quote phải khớp nguyên văn một đoạn của section (so khớp sau khi bỏ
ký hiệu Markdown, xem `text_match`) — proposal nào có 1 chunk sai bị loại toàn bộ khỏi kết quả (an toàn hơn là giữ
lại đề xuất với trích dẫn không đáng tin).

Chất lượng bộ task (báo cáo kiểm tra 02/10): lượt đầu yêu cầu phủ hết tài liệu, sắp theo trình tự làm và nêu tiên
quyết; sau đó đối chiếu độ phủ, các mục chưa có task được hỏi lại một lượt; tiên quyết chỉ giữ khi trỏ tới task có thật
nằm trước nó (không thể tạo vòng).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dto.request.portal_request_dto import AcceptAiTaskProposalRequestDTO
from src.dto.response.portal_response_dto import AiTaskProposalResponseDTO, AiTaskSourceChunkResponseDTO
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.infrastructure.observability.call_metrics import call_context
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import DocumentStatus, JobKind, VersionStatus
from src.model.job import Job
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.portal import stage_version_service, template_service
from src.services.portal.errors import PortalError
from src.services.portal.job_service import enqueue_job
from src.services.portal.proposal_options import (
    STEP_COVER,
    STEP_DRAFT,
    STEP_ORDER,
    STEP_READ,
    STEP_VERIFY,
    NullProgress,
    ProposalOptions,
    ProposalProgress,
)
from src.services.text_match import normalize_for_match, quote_matches, tidy_quote, unescape_markdown

_RULES = (
    "Quy tắc:\n"
    "1. Chỉ dùng nội dung được cung cấp, không suy diễn thêm bước nào không có trong tài liệu.\n"
    "2. PHỦ HẾT tài liệu: mọi mục nêu việc nhân viên mới phải làm (nộp hồ sơ, tham gia đào tạo, nghe nội quy, nhận thiết bị, "
    "xin phê duyệt, đăng ký...) đều phải có một task. Mục chỉ là thông tin hoặc chỉ có tiêu đề, không có hành động thì bỏ qua. "
    "Mặc định mỗi section có hành động là MỘT task riêng, đặt tên theo hành động của chính section đó; chỉ gộp hai section khi "
    "chúng mô tả đúng cùng một việc. Không tách một việc thành nhiều task nhỏ.\n"
    '3. Sắp theo thứ tự nhân viên nên làm, theo trình tự và điều kiện tài liệu nêu ("sau khi", "cuối ngày", '
    '"cần ... đồng thuận trước"). order là số thứ tự từ 1, không trùng nhau.\n'
    "4. Task chỉ làm được sau task khác (tài liệu nói rõ, hoặc hiển nhiên như cần có máy/tài khoản trước) thì ghi đúng title "
    "của task đó vào prerequisites. Tài liệu không cho thấy thì để mảng rỗng, không tự thêm.\n"
    '5. title ngắn gọn là một hành động (ví dụ "Nộp hồ sơ ngày đầu"), viết lại cho dễ đọc, không chép chữ IN HOA của tiêu đề.\n'
    "6. instructions_markdown là các bước hành động, mỗi bước một dòng, là câu đầy đủ (ai làm gì, ở đâu, gửi tới đâu). Giữ "
    "nguyên địa điểm, email, tiêu đề email, hạn chót, liên kết và tên đầu mối trong tài liệu. Không bước nào chỉ lặp lại tiêu "
    "đề hay chép nguyên câu không phải hành động. Tài liệu không nói rõ cách làm thì để instructions_markdown rỗng, đặt "
    'confidence là "LOW" và ghi lý do vào warnings.\n'
    "7. Mỗi đề xuất phải trích ít nhất 1 section bằng đúng section_id đã cho; quote là đoạn ngắn nhất đủ làm căn cứ: một đến hai "
    "câu, hoặc cả danh sách liền nhau nếu task dựa trên cả danh sách (tối đa khoảng 500 ký tự). Chép NGUYÊN VĂN từ tiêu đề hoặc nội dung "
    "của section đó (không viết lại, không ghép nhiều chỗ).\n"
)
_FIELDS = (
    "Trả về JSON là một mảng các object, mỗi object có đúng các trường: "
    "title, summary, instructions_markdown, done_criteria (mảng chuỗi), estimated_minutes (số hoặc null), "
    "source_chunks (mảng {document_section_id, quote}), confidence (HIGH|MEDIUM|LOW), warnings (mảng chuỗi), "
    "task_group (PROFILE=hồ sơ/giấy tờ, TRAINING=đào tạo/hội nhập, DEVICE=thiết bị/tài khoản, OFFICE=văn phòng/chỗ ngồi, "
    "hoặc null nếu không rõ), order (số), prerequisites (mảng title). Không thêm trường nào khác."
)
_SYSTEM_PROMPT = "Bạn giúp HR soạn task onboarding từ tài liệu nội bộ đã duyệt. " + _RULES + _FIELDS
COVERAGE_MARKER = "CHƯA có task nào"  # dấu hiệu để test phân biệt lượt bổ sung với lượt đầu
_COVERAGE_PROMPT = (
    "Bạn giúp HR soạn task onboarding từ tài liệu nội bộ đã duyệt. Các section dưới đây " + COVERAGE_MARKER + ". "
    "Với từng section có việc nhân viên mới phải làm thì đề xuất task; section chỉ là thông tin hoặc chỉ có tiêu đề "
    "thì bỏ qua (không đề xuất). Không đề xuất lại các task đã có (danh sách kèm theo). " + _RULES + _FIELDS
)

# Soạn cả bộ task cho một tài liệu cần nhiều thời gian hơn một câu trả lời của Viga (đầu ra dài).
PROPOSAL_TIMEOUT_SECONDS = 240

# Ngân sách đưa vào prompt (xấp xỉ theo số từ, như chunker): tài liệu rất dài bị cắt bớt thay vì vượt giới hạn ngữ cảnh.
PROPOSAL_TOKEN_BUDGET = 6000
# Mục quá ngắn (chỉ tiêu đề) không đáng báo "chưa có task".
MIN_COVERABLE_CHARS = 40

# Danh mục tài liệu -> nhóm task gợi ý khi AI không tự chọn được nhóm.
CATEGORY_TASK_GROUP = {
    "thiet-bi-tai-khoan": "DEVICE",
    "ho-tro-it": "DEVICE",
    "bao-mat-thong-tin": "TRAINING",
    "van-hoa": "TRAINING",
    "gioi-thieu-cong-ty": "TRAINING",
    "phan-cong-mentor-cho-ngoi": "OFFICE",
    "thu-viec": "PROFILE",
    "nghi-phep": "PROFILE",
    "phuc-loi-bao-hiem": "PROFILE",
    "quy-dinh-chung": "PROFILE",
    "onboarding": "PROFILE",
    "phap-luat-lao-dong": "PROFILE",
}


@dataclass(frozen=True)
class UncoveredSection:
    section_id: int
    heading: str | None


@dataclass
class ProposalResult:
    proposals: list[AiTaskProposalResponseDTO]
    truncated: int = 0
    uncovered: list[UncoveredSection] = field(default_factory=list)
    # Số liệu để HR/dev xem lượt chạy (không chứa nội dung): nguồn thứ tự (ai | document | single), giây từng bước, số mục AI
    # báo "chỉ là thông tin", số lô soạn song song. Đường cũ để mặc định.
    order_source: str = "legacy"
    timings: dict[str, float] = field(default_factory=dict)
    # Mục AI cho là "chỉ là thông tin" nên không tạo task: HR vẫn thấy danh sách để tự kiểm tra, không bị bỏ qua âm thầm.
    skipped_info: list[UncoveredSection] = field(default_factory=list)
    batches: int = 1


def section_text(section: DocumentSection) -> str:
    """Chữ của cả mục như người đọc thấy: tiêu đề rồi nội dung. Nhiều mục trong tài liệu thật chỉ có việc cần làm ở tiêu đề
    (nội dung chỉ là điều kiện hoặc biểu mẫu), nên trích dẫn được phép lấy từ tiêu đề."""
    return f"{section.heading}\n{section.content}" if section.heading else section.content


def _within_budget(sections: Sequence[DocumentSection]) -> tuple[list[DocumentSection], int]:
    """Giữ các section theo thứ tự tài liệu tới khi hết ngân sách; trả (section giữ lại, số section bị cắt)."""
    kept: list[DocumentSection] = []
    total = 0
    for section in sections:
        if kept and total + section.token_count > PROPOSAL_TOKEN_BUDGET:
            break
        kept.append(section)
        total += section.token_count
    return kept, len(sections) - len(kept)


def _build_user_prompt(sections: Sequence[DocumentSection], existing_titles: Sequence[str] = ()) -> str:
    parts = ["Các section của tài liệu (dùng đúng section_id khi trích):"]
    for section in sections:
        heading = section.heading or "(không có tiêu đề)"
        parts.append(f"--- section_id={section.id} · {heading} ---\n{section.content}")
    if existing_titles:
        parts.append("Các task ĐÃ CÓ (không đề xuất lại):\n" + "\n".join(f"- {title}" for title in existing_titles))
    return "\n\n".join(parts)


def _extract_items(data: object) -> list[object]:
    """JSON mode của LLM thường trả một object bọc ngoài (vd. {"tasks": [...]}) dù prompt xin một mảng."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
    raise PortalError(422, "AI_INVALID_JSON", "portal.ai_invalid_json")


def _parse_proposals(
    raw: str, section_by_id: dict[int, DocumentSection], default_group: str | None
) -> list[AiTaskProposalResponseDTO]:
    """Đọc JSON của LLM; loại đề xuất sai dạng hoặc có trích dẫn không khớp. Quote được làm sạch để hiển thị."""
    try:
        items = _extract_items(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise PortalError(422, "AI_INVALID_JSON", "portal.ai_invalid_json") from exc

    proposals: list[AiTaskProposalResponseDTO] = []
    for item in items:
        try:
            proposal = AiTaskProposalResponseDTO.model_validate(item)
        except ValidationError:
            continue
        if not proposal.source_chunks:
            continue
        chunks: list[AiTaskSourceChunkResponseDTO] = []
        for chunk in proposal.source_chunks:
            section = section_by_id.get(chunk.document_section_id)
            if section is None or not quote_matches(chunk.quote, section_text(section)):
                chunks = []
                break
            chunks.append(chunk.model_copy(update={"quote": tidy_quote(chunk.quote), "heading": section.heading}))
        if not chunks:
            continue
        update: dict[str, object] = {
            "source_chunks": chunks,
            "title": unescape_markdown(proposal.title),
            "summary": unescape_markdown(proposal.summary),
            "instructions_markdown": unescape_markdown(proposal.instructions_markdown),
            "done_criteria": [unescape_markdown(item) for item in proposal.done_criteria],
            "warnings": [unescape_markdown(item) for item in proposal.warnings],
        }
        extra_warnings = _missing_detail_warnings(proposal.model_copy(update={"source_chunks": chunks}), section_by_id)
        if extra_warnings:
            update["review_notes"] = extra_warnings
        if proposal.task_group is None and default_group is not None:
            update["task_group"] = default_group
        proposals.append(proposal.model_copy(update=update))
    return proposals


# Chi tiết dễ làm rơi khi tóm tắt: email, đường dẫn, tầng, phần trăm. Nguồn có mà hướng dẫn không nhắc tới thì cảnh báo HR kiểm tra.
_DETAIL = re.compile(r"https?://\S+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+|[Tt]ầng \d+|\d+\s?%")
MAX_DETAIL_WARNINGS = 3


def _missing_detail_warnings(
    proposal: AiTaskProposalResponseDTO, section_by_id: dict[int, DocumentSection]
) -> list[str]:
    written = normalize_for_match(
        " ".join([proposal.title, proposal.summary, proposal.instructions_markdown, *proposal.done_criteria])
    )
    seen: set[str] = set()
    missing: list[str] = []
    for chunk in proposal.source_chunks:
        section = section_by_id.get(chunk.document_section_id)
        if section is None:
            continue
        for match in _DETAIL.finditer(section_text(section).replace("\\", "")):
            detail = match.group(0).rstrip(".,;)")
            key = normalize_for_match(detail)
            if key and key not in seen and key not in written:
                seen.add(key)
                missing.append(detail if len(detail) <= 60 else detail[:57] + "…")
    return [
        f"Nguồn có “{detail}” nhưng hướng dẫn chưa nhắc tới; HR kiểm tra lại."
        for detail in missing[:MAX_DETAIL_WARNINGS]
    ]


def _position(proposal: AiTaskProposalResponseDTO, section_by_id: dict[int, DocumentSection]) -> int:
    """Vị trí của task trong tài liệu: chỉ số của mục đầu tiên nó trích."""
    indexes = [
        section_by_id[chunk.document_section_id].section_index
        for chunk in proposal.source_chunks
        if chunk.document_section_id in section_by_id
    ]
    return min(indexes) if indexes else 0


# Việc tài liệu gắn với "cuối ngày" (vd. ký hợp đồng theo email cuối ngày) xếp sau mọi việc khác trong cùng lượt.
_END_OF_DAY = re.compile(r"cuối ngày", re.IGNORECASE)


def _is_end_of_day(proposal: AiTaskProposalResponseDTO) -> bool:
    return bool(
        _END_OF_DAY.search(
            " ".join([proposal.title, proposal.summary, *(chunk.quote for chunk in proposal.source_chunks)])
        )
    )


def _arrange(
    first: list[AiTaskProposalResponseDTO],
    extra: list[AiTaskProposalResponseDTO],
    section_by_id: dict[int, DocumentSection],
) -> list[AiTaskProposalResponseDTO]:
    """Sắp theo `order` AI đưa ra (thiếu thì theo vị trí trong tài liệu); task bổ sung chèn theo vị trí tài liệu; rồi đánh số
    lại 1..n và giữ các tiên quyết hợp lệ (tên có thật, nằm trước, khác chính nó)."""
    ordered = sorted(first, key=lambda p: (p.order is None, p.order or 0, _position(p, section_by_id)))
    for item in sorted(extra, key=lambda p: _position(p, section_by_id)):
        index = max(
            (
                i
                for i, existing in enumerate(ordered)
                if _position(existing, section_by_id) <= _position(item, section_by_id)
            ),
            default=-1,
        )
        ordered.insert(index + 1, item)

    ordered = [p for p in ordered if not _is_end_of_day(p)] + [p for p in ordered if _is_end_of_day(p)]

    titles_before: list[str] = []
    result: list[AiTaskProposalResponseDTO] = []
    for number, proposal in enumerate(ordered, start=1):
        prerequisites = list(dict.fromkeys(name for name in proposal.prerequisites if name in titles_before))
        result.append(proposal.model_copy(update={"order": number, "prerequisites": prerequisites}))
        titles_before.append(proposal.title)
    return result


async def propose_tasks(
    session: AsyncSession,
    *,
    document_version_id: int,
    llm: ChatCompletionPort,
    options: ProposalOptions | None = None,
) -> list[AiTaskProposalResponseDTO]:
    result = await propose_tasks_detailed(session, document_version_id=document_version_id, llm=llm, options=options)
    return result.proposals


async def propose_tasks_with_meta(
    session: AsyncSession,
    *,
    document_version_id: int,
    llm: ChatCompletionPort,
    options: ProposalOptions | None = None,
) -> tuple[list[AiTaskProposalResponseDTO], int]:
    """Như `propose_tasks`, kèm số section bị cắt vì vượt ngân sách prompt (để giao diện cảnh báo HR)."""
    result = await propose_tasks_detailed(session, document_version_id=document_version_id, llm=llm, options=options)
    return result.proposals, result.truncated


# ---------------------------------------------------------------------------------------------------------------------
# Đường nhanh (kế hoạch tối ưu độ trễ, Ai-task/ke-hoach-toi-uu-tao-task-bang-ai.md mục 8). Khác đường cũ ở bốn điểm:
# 1. tắt suy luận ẩn (chiếm 83–86% thời gian đo thật) — chất lượng đã so ở kế hoạch;
# 2. AI KHÔNG chép nguyên văn quote mà chỉ chỉ số dòng; backend dựng quote từ chữ gốc rồi vẫn kiểm bằng `quote_matches`;
# 3. mục AI báo "chỉ là thông tin" (skipped_sections) không bị hỏi lại ở lượt bù phủ;
# 4. thứ tự và tiên quyết do một lời gọi nhỏ quyết, kết quả được kiểm (hoán vị, chỉ trỏ về task đứng trước) hoặc quay về thứ tự tài liệu.
# ---------------------------------------------------------------------------------------------------------------------
_FAST_RULES = (
    "Bạn giúp HR soạn task onboarding từ tài liệu nội bộ đã duyệt. Chỉ dùng nội dung được cung cấp. Mặc định mỗi section có hành động "
    "là MỘT task riêng, đặt tên theo hành động; section chỉ là thông tin thì bỏ qua. title ngắn gọn là một hành động. steps là các bước "
    "hành động, mỗi bước một câu đầy đủ, giữ nguyên địa điểm, email, tiêu đề email, hạn chót, liên kết, tên đầu mối. "
    "Tài liệu không nói rõ cách làm thì để steps rỗng và ghi lý do vào warnings. "
    "Nguồn: KHÔNG chép lại câu, chỉ ghi sources = [{section_id, from_line, to_line}] theo số dòng L<n> đã đánh (L0 là tiêu đề), chọn đoạn ngắn nhất đủ làm căn cứ. "
    "needs = các câu điều kiện nguyên văn nếu task chỉ làm được sau việc khác (hoặc rỗng). "
    "Section chỉ là thông tin, không có việc nào cho nhân viên thì không tạo task và ghi section_id của nó vào skipped_sections. "
    'Trả JSON {"tasks":[{"title","summary","steps":[...],"done_criteria":[...],"estimated_minutes":số|null,"sources":[...],'
    '"task_group":"PROFILE|TRAINING|DEVICE|OFFICE|null","needs":[...],"warnings":[...]}],"skipped_sections":[section_id,...]}.'
)
_FAST_COVERAGE_RULES = (
    _FAST_RULES + " CÁC MỤC DƯỚI ĐÂY CHƯA CÓ TASK: mỗi mục có hành động cho nhân viên phải có task riêng; "
    "chỉ bỏ qua mục thuần thông tin (ghi vào skipped_sections)."
)
_ORDER_SYSTEM = (
    "Bạn sắp xếp các task onboarding của một tài liệu. Cho danh sách task đánh số kèm điều kiện nguyên văn (needs). "
    'Trả JSON {"order":[các số theo thứ tự nên làm, việc gắn với "cuối ngày" xếp cuối],"prerequisites":{"<số>":[các số phải xong trước]}}. '
    "Chỉ thêm tiên quyết khi tài liệu cho thấy rõ (needs hoặc hiển nhiên như cần có máy/tài khoản trước). Không tạo vòng."
)
MAX_PREREQUISITES = 3
# Nhiệt độ 0 cho mọi lời gọi của đường nhanh: đo thật trên file docx không tiêu đề, số task giữa 8 lần chạy từ 12–29 (mặc định)
# xuống 12–14; trên "Hướng dẫn ngày 1" từ 13–16 xuống 16–17 (`thu-nghiem/ket-qua-13-nhiet-do.json`).
FAST_TEMPERATURE = 0.0
MAX_QUOTE_CHARS = 600
COVERAGE_GROUP_SIZE = 4


@dataclass
class _Draft:
    proposal: AiTaskProposalResponseDTO
    needs: list[str]
    position: int  # chỉ số mục đầu tiên task trích: thứ tự dự phòng khi AI xếp hỏng


def _lines_of(section: DocumentSection) -> list[str]:
    """Các dòng đánh số của một mục: L0 là tiêu đề (có thể rỗng), L1.. là từng dòng nội dung không rỗng."""
    return [section.heading or ""] + [line.rstrip() for line in section.content.split("\n") if line.strip()]


def _numbered_prompt(sections: Sequence[DocumentSection]) -> str:
    blocks = []
    for section in sections:
        numbered = "\n".join(f"L{index}: {line}" for index, line in enumerate(_lines_of(section)))
        blocks.append(f"--- section_id={section.id} ---\n{numbered}")
    return "\n\n".join(blocks)


def _number(value: object) -> int | None:
    """Mô hình hay viết "L3" thay vì 3 (đo thật: 631 tham chiếu): đọc được cả hai dạng."""
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _quote_from_lines(source: dict[str, object], section_by_id: dict[int, DocumentSection]) -> tuple[int, str] | None:
    """Dựng quote từ số dòng AI chỉ; trả None nếu mục không thuộc tài liệu, số dòng sai, hoặc chữ dựng ra không khớp bản gốc."""
    section_id = _number(source.get("section_id"))
    first, last = _number(source.get("from_line")), _number(source.get("to_line"))
    section = section_by_id.get(section_id) if section_id is not None else None
    if section is None or first is None or last is None:
        return None
    lines = _lines_of(section)
    if first > last:
        first, last = last, first
    last = min(last, len(lines) - 1)
    if not 0 <= first < len(lines):
        return None
    chosen: list[str] = []
    size = 0
    for line in lines[first : last + 1]:
        if chosen and size + len(line) > MAX_QUOTE_CHARS:
            break  # đoạn dài hơn mức đọc được: giữ phần đầu, vẫn cắt theo ranh giới dòng nên còn nguyên văn
        chosen.append(line)
        size += len(line) + 1
    quote = "\n".join(chosen).strip()
    if not quote or not quote_matches(quote, section_text(section)):
        return None
    return section.id, quote


def _text_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return (
        [unescape_markdown(str(item)).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
    )


def _parse_fast(
    raw: str, section_by_id: dict[int, DocumentSection], default_group: str | None
) -> tuple[list[_Draft], set[int]]:
    """Đọc JSON của đường nhanh. Trả (các bản nháp đã kiểm nguồn, các mục AI báo "chỉ là thông tin").

    Bản nháp không dựng được nguồn nào hợp lệ bị loại (cùng nguyên tắc đường cũ: không giữ đề xuất với trích dẫn không tin được).
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PortalError(422, "AI_INVALID_JSON", "portal.ai_invalid_json") from exc
    if isinstance(data, dict):
        items = data.get("tasks")
        skipped_raw = data.get("skipped_sections")
    else:
        items, skipped_raw = data, None
    if not isinstance(items, list):
        raise PortalError(422, "AI_INVALID_JSON", "portal.ai_invalid_json")
    skipped = (
        {n for n in (_number(value) for value in skipped_raw) if n is not None}
        if isinstance(skipped_raw, list)
        else set()
    )

    drafts: list[_Draft] = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("title") or "").strip():
            continue
        sources = [s for s in (item.get("sources") or []) if isinstance(s, dict)]
        chunks: list[AiTaskSourceChunkResponseDTO] = []
        for source in sources:
            built = _quote_from_lines(source, section_by_id)
            if built is None:
                continue
            section_id, quote = built
            shown = tidy_quote(quote)
            # Quote HIỂN THỊ (đã làm sạch) cũng phải khớp lại bản gốc: HR bấm tạo task thì `create_task_from_proposal` kiểm đúng chuỗi này.
            if not quote_matches(shown, section_text(section_by_id[section_id])):
                continue
            chunks.append(
                AiTaskSourceChunkResponseDTO(
                    document_section_id=section_id, quote=shown, heading=section_by_id[section_id].heading
                )
            )
        if not chunks:
            continue
        steps = _text_list(item.get("steps"))
        try:
            minutes = int(item["estimated_minutes"]) if item.get("estimated_minutes") is not None else None
        except (TypeError, ValueError):
            minutes = None
        group = str(item.get("task_group") or "").upper()
        proposal = AiTaskProposalResponseDTO(
            title=unescape_markdown(str(item["title"])).strip(),
            summary=unescape_markdown(str(item.get("summary") or "")).strip(),
            instructions_markdown="\n".join(steps),
            done_criteria=_text_list(item.get("done_criteria")),
            estimated_minutes=minutes if minutes and minutes > 0 else None,
            source_chunks=chunks,
            confidence="LOW" if not steps else "HIGH",
            warnings=_text_list(item.get("warnings")),
            task_group=group if group in {"PROFILE", "TRAINING", "DEVICE", "OFFICE"} else default_group,
        )
        notes = _missing_detail_warnings(proposal, section_by_id)
        if notes:
            proposal = proposal.model_copy(update={"review_notes": notes, "confidence": "MEDIUM" if steps else "LOW"})
        drafts.append(
            _Draft(proposal=proposal, needs=_text_list(item.get("needs")), position=_position(proposal, section_by_id))
        )
    return drafts, skipped


def _split_batches(sections: Sequence[DocumentSection], batch_words: int) -> list[list[DocumentSection]]:
    """Chia theo ngân sách từ, giữ thứ tự tài liệu. Tài liệu vừa một lô thì chỉ một lời gọi (đã đo: giữ được ngữ cảnh toàn tài liệu)."""
    batches: list[list[DocumentSection]] = []
    current: list[DocumentSection] = []
    words = 0
    for section in sections:
        if current and words + section.token_count > batch_words:
            batches.append(current)
            current, words = [], 0
        current.append(section)
        words += section.token_count
    if current:
        batches.append(current)
    return batches


def _same_title(a: str, b: str) -> bool:
    return normalize_for_match(a) == normalize_for_match(b)


def _document_order(drafts: list[_Draft]) -> list[int]:
    """Thứ tự dự phòng: theo vị trí trong tài liệu, việc "cuối ngày" sau cùng. Trả chỉ số (0-based) của `drafts`."""
    indexes = list(range(len(drafts)))
    return sorted(indexes, key=lambda i: (_is_end_of_day(drafts[i].proposal), drafts[i].position, i))


def _apply_order(drafts: list[_Draft], data: object) -> tuple[list[int], dict[int, list[int]]] | None:
    """Kiểm kết quả xếp thứ tự của AI. Trả (thứ tự 0-based, tiên quyết theo chỉ số 0-based) hoặc None nếu không dùng được."""
    if not isinstance(data, dict):
        return None
    order_raw = data.get("order")
    if not isinstance(order_raw, list):
        return None
    numbers = [_number(value) for value in order_raw]
    count = len(drafts)
    if None in numbers or sorted(n for n in numbers if n is not None) != list(range(1, count + 1)):
        return None  # phải đúng một hoán vị của 1..n: thiếu hay trùng đều bỏ
    order = [n - 1 for n in numbers if n is not None]
    # Quy tắc của tài liệu "việc gắn với cuối ngày xếp sau mọi việc khác" do mã bảo đảm (như đường cũ), không chỉ nhờ AI nhớ.
    # Làm TRƯỚC khi kiểm tiên quyết để tiên quyết trỏ tới việc cuối ngày bị đẩy ra sau sẽ tự bị loại.
    order = [i for i in order if not _is_end_of_day(drafts[i].proposal)] + [
        i for i in order if _is_end_of_day(drafts[i].proposal)
    ]
    rank = {index: place for place, index in enumerate(order)}
    prerequisites: dict[int, list[int]] = {}
    raw_prerequisites = data.get("prerequisites")
    if isinstance(raw_prerequisites, dict):
        for key, values in raw_prerequisites.items():
            target = _number(key)
            if target is None or not 1 <= target <= count or not isinstance(values, list):
                continue
            kept: list[int] = []
            for value in values:
                source = _number(value)
                # Chỉ giữ tiên quyết trỏ tới task có thật và đứng TRƯỚC trong thứ tự mới: không thể tạo vòng.
                if (
                    source is not None
                    and 1 <= source <= count
                    and source != target
                    and rank[source - 1] < rank[target - 1]
                ):
                    if source - 1 not in kept:
                        kept.append(source - 1)
            if kept:
                prerequisites[target - 1] = kept[:MAX_PREREQUISITES]
    return order, prerequisites


async def _order_drafts(
    drafts: list[_Draft], llm: ChatCompletionPort, options: ProposalOptions
) -> tuple[list[AiTaskProposalResponseDTO], str]:
    """Xếp thứ tự và tiên quyết. Trả (danh sách đã đánh số 1..n, nguồn thứ tự: "ai" | "document" | "single")."""
    if len(drafts) <= 1:
        placed = [d.proposal.model_copy(update={"order": 1, "prerequisites": []}) for d in drafts]
        return placed, "single"
    base = sorted(range(len(drafts)), key=lambda i: (drafts[i].position, i))
    ordered_drafts = [drafts[i] for i in base]  # số thứ tự gửi cho AI là thứ tự tài liệu
    listing = "\n".join(
        f"{number}. {d.proposal.title} | {d.proposal.summary} | needs: {' / '.join(d.needs) or '-'}"
        for number, d in enumerate(ordered_drafts, start=1)
    )
    applied: tuple[list[int], dict[int, list[int]]] | None = None
    prerequisites: dict[int, list[int]]
    try:
        with call_context(operation="task.proposal"):
            raw = await llm.complete_json(
                system_prompt=_ORDER_SYSTEM,
                user_prompt=listing,
                timeout_seconds=options.call_timeout_seconds,
                reasoning=False,
                stream=True,
                temperature=FAST_TEMPERATURE,
            )
        applied = _apply_order(ordered_drafts, json.loads(raw))
    except (ChatCompletionError, ValueError):
        applied = None
    if applied is None:
        fallback = _document_order(ordered_drafts)
        order = fallback
        prerequisites = {}
        source = "document"
    else:
        order, prerequisites = applied
        source = "ai"
    place = {index: number for number, index in enumerate(order, start=1)}
    result: list[AiTaskProposalResponseDTO] = []
    for index in order:
        names = [ordered_drafts[j].proposal.title for j in prerequisites.get(index, [])]
        result.append(
            ordered_drafts[index].proposal.model_copy(
                update={"order": place[index], "prerequisites": list(dict.fromkeys(names))}
            )
        )
    return result, source


async def _ask_fast(
    sections: Sequence[DocumentSection], system_prompt: str, llm: ChatCompletionPort, options: ProposalOptions
) -> str:
    with call_context(operation="task.proposal"):
        return await llm.complete_json(
            system_prompt=system_prompt,
            user_prompt=_numbered_prompt(sections),
            timeout_seconds=options.call_timeout_seconds,
            reasoning=False,
            stream=True,
            temperature=FAST_TEMPERATURE,
        )


async def _run_batches(
    batches: list[list[DocumentSection]],
    system_prompt: str,
    llm: ChatCompletionPort,
    options: ProposalOptions,
    section_by_id: dict[int, DocumentSection],
    default_group: str | None,
    on_done: Callable[[int, int], Awaitable[None]],
) -> tuple[list[_Draft], set[int], list[BaseException]]:
    """Chạy các lô song song. Lô hỏng không làm mất lô khác: lỗi được trả về để người gọi quyết (mục của lô hỏng sẽ được bù phủ)."""
    drafts: list[_Draft] = []
    skipped: set[int] = set()
    errors: list[BaseException] = []
    finished = 0

    async def one(batch: list[DocumentSection]) -> None:
        nonlocal finished
        try:
            raw = await _ask_fast(batch, system_prompt, llm, options)
            batch_drafts, batch_skipped = _parse_fast(raw, section_by_id, default_group)
            drafts.extend(batch_drafts)
            skipped.update(batch_skipped)
        except (ChatCompletionError, PortalError) as exc:
            errors.append(exc)
        finished += 1
        await on_done(finished, len(batches))

    await asyncio.gather(*(one(batch) for batch in batches))
    return drafts, skipped, errors


async def _propose_fast(
    kept: list[DocumentSection],
    truncated: int,
    default_group: str | None,
    llm: ChatCompletionPort,
    options: ProposalOptions,
    progress: ProposalProgress,
) -> ProposalResult:
    section_by_id = {section.id: section for section in kept}
    timings: dict[str, float] = {}

    async def timed(name: str, started: float) -> None:
        timings[name] = round(time.perf_counter() - started, 2)

    # Bước 2-3: soạn theo lô (song song) rồi kiểm nguồn (đã làm ngay khi đọc từng lô, ở đây chỉ báo bước).
    started = time.perf_counter()
    batches = _split_batches(kept, options.batch_words)
    await progress.update(STEP_DRAFT, done=0, total=len(batches))

    async def draft_done(done: int, total: int) -> None:
        await progress.update(STEP_DRAFT, done=done, total=total)

    drafts, skipped, errors = await _run_batches(
        batches, _FAST_RULES, llm, options, section_by_id, default_group, draft_done
    )
    await timed("draft", started)
    if not drafts and errors and len(errors) == len(batches):
        raise errors[0]  # mọi lô đều hỏng: không có gì để bù phủ, báo lỗi thật thay vì trả danh sách rỗng
    await progress.update(STEP_VERIFY, done=1, total=1)

    # Bước 4: bù phủ MỘT lượt cho mục có nội dung mà chưa task nào trích và AI cũng không báo "chỉ là thông tin".
    def uncited() -> list[DocumentSection]:
        cited = {chunk.document_section_id for d in drafts for chunk in d.proposal.source_chunks}
        return [
            s
            for s in kept
            if s.id not in cited and s.id not in skipped and len(section_text(s).strip()) >= MIN_COVERABLE_CHARS
        ]

    missing = uncited()
    if missing:
        started = time.perf_counter()
        groups = [missing[i : i + COVERAGE_GROUP_SIZE] for i in range(0, len(missing), COVERAGE_GROUP_SIZE)]
        await progress.update(STEP_COVER, done=0, total=len(groups))

        async def cover_done(done: int, total: int) -> None:
            await progress.update(STEP_COVER, done=done, total=total)

        extra, extra_skipped, _ = await _run_batches(
            groups, _FAST_COVERAGE_RULES, llm, options, section_by_id, default_group, cover_done
        )
        skipped |= extra_skipped
        drafts.extend(d for d in extra if not any(_same_title(d.proposal.title, e.proposal.title) for e in drafts))
        await timed("cover", started)
    else:
        await progress.skip(STEP_COVER)

    # Bước 5: thứ tự và tiên quyết.
    started = time.perf_counter()
    if len(drafts) > 1:
        await progress.update(STEP_ORDER, done=0, total=1)
    proposals, order_source = await _order_drafts(drafts, llm, options)
    if len(drafts) > 1:
        await progress.update(STEP_ORDER, done=1, total=1)
        await timed("order", started)
    else:
        await progress.skip(STEP_ORDER)

    cited_after = {chunk.document_section_id for p in proposals for chunk in p.source_chunks}
    uncovered = [
        UncoveredSection(section_id=s.id, heading=s.heading)
        for s in kept
        if s.id not in cited_after and s.id not in skipped and len(section_text(s).strip()) >= MIN_COVERABLE_CHARS
    ]
    skipped_info = [
        UncoveredSection(section_id=s.id, heading=s.heading)
        for s in kept
        if s.id in skipped and s.id not in cited_after and len(section_text(s).strip()) >= MIN_COVERABLE_CHARS
    ]
    return ProposalResult(
        proposals=proposals,
        truncated=truncated,
        uncovered=uncovered,
        order_source=order_source,
        timings=timings,
        skipped_info=skipped_info,
        batches=len(batches),
    )


async def _propose_legacy(
    kept: list[DocumentSection], truncated: int, default_group: str | None, llm: ChatCompletionPort
) -> ProposalResult:
    """Đường cũ (`task_proposal_mode=legacy`): suy luận bật, AI chép nguyên văn quote, bù phủ tối đa một lượt."""
    section_by_id = {section.id: section for section in kept}

    with call_context(operation="task.proposal"):
        raw = await llm.complete_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(kept),
            timeout_seconds=PROPOSAL_TIMEOUT_SECONDS,
        )
    first = _parse_proposals(raw, section_by_id, default_group)

    # Đối chiếu độ phủ: mục có nội dung mà chưa task nào trích thì hỏi lại đúng các mục đó một lượt.
    cited = {chunk.document_section_id for proposal in first for chunk in proposal.source_chunks}
    missing = [s for s in kept if s.id not in cited and len(section_text(s).strip()) >= MIN_COVERABLE_CHARS]
    extra: list[AiTaskProposalResponseDTO] = []
    if missing:
        try:
            with call_context(operation="task.proposal"):
                raw_extra = await llm.complete_json(
                    system_prompt=_COVERAGE_PROMPT,
                    user_prompt=_build_user_prompt(missing, [proposal.title for proposal in first]),
                    timeout_seconds=PROPOSAL_TIMEOUT_SECONDS,
                )
            known = {proposal.title for proposal in first}
            extra = [
                p
                for p in _parse_proposals(raw_extra, {s.id: s for s in missing}, default_group)
                if p.title not in known
            ]
        except PortalError:
            extra = []  # lượt bổ sung hỏng không làm mất kết quả lượt đầu; mục thiếu vẫn được liệt kê cho HR

    proposals = _arrange(first, extra, section_by_id)
    cited_after = {chunk.document_section_id for proposal in proposals for chunk in proposal.source_chunks}
    uncovered = [
        UncoveredSection(section_id=s.id, heading=s.heading)
        for s in kept
        if s.id not in cited_after and len(section_text(s).strip()) >= MIN_COVERABLE_CHARS
    ]
    return ProposalResult(proposals=proposals, truncated=truncated, uncovered=uncovered)


async def propose_tasks_detailed(
    session: AsyncSession,
    *,
    document_version_id: int,
    llm: ChatCompletionPort,
    options: ProposalOptions | None = None,
    progress: ProposalProgress | None = None,
) -> ProposalResult:
    options = options or ProposalOptions()
    progress = progress or NullProgress()
    sections = (
        await session.scalars(
            select(DocumentSection)
            .where(DocumentSection.version_id == document_version_id)
            .order_by(DocumentSection.section_index)
        )
    ).all()
    if not sections:
        raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
    kept, truncated = _within_budget(sections)

    category_slug = await session.scalar(
        select(DocumentCategory.slug)
        .join(Document, Document.category_id == DocumentCategory.id)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .where(DocumentVersion.id == document_version_id)
    )
    default_group = CATEGORY_TASK_GROUP.get(category_slug or "")
    await progress.update(STEP_READ, done=1, total=1)
    if options.mode == "legacy":
        await progress.update(STEP_DRAFT, done=0, total=1)
        result = await _propose_legacy(kept, truncated, default_group, llm)
        await progress.update(STEP_DRAFT, done=1, total=1)
        for step in (STEP_VERIFY, STEP_COVER, STEP_ORDER):
            await progress.skip(step)
        return result
    return await _propose_fast(kept, truncated, default_group, llm, options, progress)


def compose_task_body(payload: AcceptAiTaskProposalRequestDTO) -> str:
    """Ghép nội dung task theo ba mục cố định để tab "Hướng dẫn" hiện đúng (cùng định dạng với `taskBody.ts` ở giao diện).

    Không có trường tách riêng (client cũ chỉ gửi `instructions_markdown`) thì giữ nguyên văn như trước.
    """
    if payload.summary is None and not payload.done_criteria:
        return payload.instructions_markdown
    why_lines = [payload.summary.strip()] if payload.summary and payload.summary.strip() else []
    if payload.estimated_minutes:
        why_lines.append(f"Ước tính khoảng {payload.estimated_minutes} phút.")
    why_lines.extend(f"Lưu ý: {warning.strip()}" for warning in payload.warnings if warning.strip())
    steps = [
        re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", line).strip()
        for line in payload.instructions_markdown.splitlines()
        if line.strip()
    ]
    parts: list[str] = []
    if why_lines:
        parts.append("## Vì sao phải làm\n" + "\n".join(why_lines))
    done = [item.strip() for item in payload.done_criteria if item.strip()]
    if done:
        parts.append("## Điều kiện hoàn thành\n" + "\n".join(f"- {item}" for item in done))
    if steps:
        parts.append("## Các bước\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1)))
    return "\n\n".join(parts) if parts else payload.instructions_markdown


async def load_stage_and_template(session: AsyncSession, stage_id: int) -> tuple[JourneyStage, JourneyTemplate]:
    stage = await session.get(JourneyStage, stage_id)
    if stage is None:
        raise PortalError(404, "STAGE_NOT_FOUND", "portal.stage_not_found")
    template = await session.get(JourneyTemplate, stage.journey_template_id)
    if template is None:
        raise PortalError(404, "JOURNEY_TEMPLATE_NOT_FOUND", "portal.journey_template_not_found")
    return stage, template


async def create_task_from_proposal(
    session: AsyncSession,
    *,
    stage: JourneyStage,
    template: JourneyTemplate,
    payload: AcceptAiTaskProposalRequestDTO,
    user: User,
) -> TaskTemplate:
    """Tạo task từ đề xuất vào một BẢN NHÁP của ngày (`payload.stage_version_id`, không có thì bản nháp mới nhất; chưa có
    nháp thì tạo từ bản đang áp dụng). Không bao giờ ghi vào bản đang áp dụng."""
    # Kiểm lại nguồn trước khi ghi gì: section phải có thật và `quote` phải là đoạn nguyên văn của đúng section đó
    # (không tin dữ liệu client gửi lên chỉ vì lúc đề xuất đã kiểm).
    sources: list[tuple[DocumentSection, str | None]] = []
    for chunk in payload.source_chunks:
        section = await session.get(DocumentSection, chunk.document_section_id)
        if section is None or (chunk.quote and not quote_matches(chunk.quote, section_text(section))):
            raise PortalError(422, "INVALID_SOURCE_CHUNK", "portal.invalid_source_chunk")
        sources.append((section, tidy_quote(chunk.quote) if chunk.quote else None))

    if payload.stage_version_id is not None:
        target = await stage_version_service.get_version(session, payload.stage_version_id)
        if target.journey_stage_id != stage.id:
            raise PortalError(422, "STAGE_OUT_OF_TEMPLATE", "portal.stage_out_of_template")
    else:
        target = await stage_version_service.working_draft(session, stage, user)
    stage_version_service.ensure_editable(target)

    task = TaskTemplate(
        journey_stage_id=stage.id,
        stage_version_id=target.id,
        title=payload.title,
        body_markdown=compose_task_body(payload),
        required=payload.required,
        task_group=payload.task_group,
        sort_order=0,
        team_id=template.team_id,
    )
    session.add(task)
    await session.flush()
    # Xếp cuối giai đoạn (đánh số 1..n theo thứ tự tạo) và gắn tiên quyết nếu có: thứ tự đề xuất của AI thành thứ tự thật.
    await template_service.place_in_version(session, task=task, version=target, position=None)
    await template_service.apply_dependencies(
        session, task=task, version_id=target.id, depends_on=list(dict.fromkeys(payload.depends_on))
    )

    for section, quote in sources:
        version = await session.get(DocumentVersion, section.version_id)
        assert version is not None  # FK đảm bảo section luôn có version hợp lệ
        session.add(
            TaskSourceMapping(
                task_template_id=task.id,
                document_id=version.document_id,
                document_version_id=version.id,
                document_section_id=section.id,
                quote=quote,
            )
        )
    await session.commit()
    return task


async def enqueue_proposal_job(session: AsyncSession, *, user: User, version_ids: Sequence[int]) -> Job:
    """Xếp job tạo task bằng AI cho nhiều tài liệu (chạy nền, có phần trăm — mục 14.5).

    Chỉ nhận phiên bản đã kích hoạt (có section) của tài liệu còn dùng; bản nháp chưa có section nên không phân tích được.
    """
    unique_ids = sorted(set(version_ids))
    rows = (
        await session.execute(
            select(DocumentVersion.id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                DocumentVersion.id.in_(unique_ids),
                DocumentVersion.status == VersionStatus.ACTIVE,
                Document.status == DocumentStatus.ACTIVE,
            )
        )
    ).all()
    if len(rows) != len(unique_ids):
        raise PortalError(422, "VERSION_NOT_USABLE", "portal.version_not_usable")
    digest = hashlib.sha256(",".join(str(v) for v in unique_ids).encode()).hexdigest()[:16]
    return await enqueue_job(
        session,
        kind=JobKind.AI_TASK_PROPOSAL.value,
        payload={"version_ids": unique_ids},
        idempotency_key=f"ai-proposal:{user.id}:{digest}",
        created_by=user.id,
        # Lỗi tạm thời của dịch vụ AI (mọi tài liệu đều không gọi được) được thử lại một lần; xem `run_ai_task_proposal`.
        max_attempts=2,
    )
