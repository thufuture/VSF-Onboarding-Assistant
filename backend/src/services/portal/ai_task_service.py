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

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dto.request.portal_request_dto import AcceptAiTaskProposalRequestDTO
from src.dto.response.portal_response_dto import AiTaskProposalResponseDTO, AiTaskSourceChunkResponseDTO
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.call_metrics import call_context
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import DocumentStatus, JobKind, JourneyTemplateStatus, VersionStatus
from src.model.job import Job
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.portal import template_service
from src.services.portal.errors import PortalError
from src.services.portal.job_service import enqueue_job
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
    session: AsyncSession, *, document_version_id: int, llm: ChatCompletionPort
) -> list[AiTaskProposalResponseDTO]:
    result = await propose_tasks_detailed(session, document_version_id=document_version_id, llm=llm)
    return result.proposals


async def propose_tasks_with_meta(
    session: AsyncSession, *, document_version_id: int, llm: ChatCompletionPort
) -> tuple[list[AiTaskProposalResponseDTO], int]:
    """Như `propose_tasks`, kèm số section bị cắt vì vượt ngân sách prompt (để giao diện cảnh báo HR)."""
    result = await propose_tasks_detailed(session, document_version_id=document_version_id, llm=llm)
    return result.proposals, result.truncated


async def propose_tasks_detailed(
    session: AsyncSession, *, document_version_id: int, llm: ChatCompletionPort
) -> ProposalResult:
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
    section_by_id = {section.id: section for section in kept}

    category_slug = await session.scalar(
        select(DocumentCategory.slug)
        .join(Document, Document.category_id == DocumentCategory.id)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .where(DocumentVersion.id == document_version_id)
    )
    default_group = CATEGORY_TASK_GROUP.get(category_slug or "")

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
    if template.status != JourneyTemplateStatus.DRAFT:
        raise PortalError(409, "TEMPLATE_ALREADY_PUBLISHED", "portal.template_already_published")
    return stage, template


async def create_task_from_proposal(
    session: AsyncSession, *, stage: JourneyStage, template: JourneyTemplate, payload: AcceptAiTaskProposalRequestDTO
) -> TaskTemplate:
    # Kiểm lại nguồn trước khi ghi gì: section phải có thật và `quote` phải là đoạn nguyên văn của đúng section đó
    # (không tin dữ liệu client gửi lên chỉ vì lúc đề xuất đã kiểm).
    sources: list[tuple[DocumentSection, str | None]] = []
    for chunk in payload.source_chunks:
        section = await session.get(DocumentSection, chunk.document_section_id)
        if section is None or (chunk.quote and not quote_matches(chunk.quote, section_text(section))):
            raise PortalError(422, "INVALID_SOURCE_CHUNK", "portal.invalid_source_chunk")
        sources.append((section, tidy_quote(chunk.quote) if chunk.quote else None))

    task = TaskTemplate(
        journey_stage_id=stage.id,
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
    await template_service.place_in_stage(session, task=task, stage_id=stage.id, position=None)
    await template_service.apply_dependencies(
        session, task=task, template_id=template.id, depends_on=list(dict.fromkeys(payload.depends_on))
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
        max_attempts=1,
    )
