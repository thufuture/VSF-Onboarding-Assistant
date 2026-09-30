"""AI đề xuất task từ tài liệu đã ingest — P4B mục 8.4/8.5.

Đề xuất KHÔNG được lưu DB cho tới khi HR "accept" (P0A §3: AI chỉ đề xuất, HR quyết). Mọi source_chunk
phải thuộc đúng document_version đã chọn và quote phải là chuỗi con nguyên văn của section — proposal nào
có 1 chunk sai bị loại toàn bộ khỏi kết quả (an toàn hơn là giữ lại đề xuất với trích dẫn không đáng tin).
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dto.request.portal_request_dto import AcceptAiTaskProposalRequestDTO
from src.dto.response.portal_response_dto import AiTaskProposalResponseDTO
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import JourneyTemplateStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.services.portal.errors import PortalError

_SYSTEM_PROMPT = (
    "Bạn giúp HR soạn task onboarding từ tài liệu nội bộ đã duyệt. "
    "Chỉ dùng đúng nội dung được cung cấp trong các section dưới đây, không suy diễn thêm bước nào "
    "không có trong tài liệu. Mỗi đề xuất phải trích ít nhất 1 section bằng đúng section_id đã cho, "
    "quote phải là câu nguyên văn lấy từ nội dung section đó. Nếu tài liệu không nói rõ cách làm, "
    'đặt confidence là "LOW". Trả về JSON là một mảng các object, mỗi object có đúng các trường: '
    "title, summary, instructions_markdown, done_criteria (mảng chuỗi), estimated_minutes (số hoặc null), "
    "source_chunks (mảng {document_section_id, quote}), confidence (HIGH|MEDIUM|LOW), warnings (mảng chuỗi). "
    "Không thêm trường nào khác."
)


def _build_user_prompt(sections: Sequence[DocumentSection]) -> str:
    parts = ["Các section của tài liệu (dùng đúng section_id khi trích):"]
    for section in sections:
        heading = section.heading or "(không có tiêu đề)"
        parts.append(f"--- section_id={section.id} · {heading} ---\n{section.content}")
    return "\n\n".join(parts)


async def propose_tasks(
    session: AsyncSession, *, document_version_id: int, llm: ChatCompletionPort
) -> list[AiTaskProposalResponseDTO]:
    sections = (
        await session.scalars(
            select(DocumentSection)
            .where(DocumentSection.version_id == document_version_id)
            .order_by(DocumentSection.section_index)
        )
    ).all()
    if not sections:
        raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
    section_by_id = {section.id: section for section in sections}

    raw = await llm.complete_json(system_prompt=_SYSTEM_PROMPT, user_prompt=_build_user_prompt(sections))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PortalError(422, "AI_INVALID_JSON", "portal.ai_invalid_json") from exc
    if not isinstance(data, list):
        raise PortalError(422, "AI_INVALID_JSON", "portal.ai_invalid_json")

    proposals: list[AiTaskProposalResponseDTO] = []
    for item in data:
        try:
            proposal = AiTaskProposalResponseDTO.model_validate(item)
        except ValidationError:
            continue
        if not proposal.source_chunks:
            continue
        valid = True
        for chunk in proposal.source_chunks:
            section = section_by_id.get(chunk.document_section_id)
            if section is None or chunk.quote not in section.content:
                valid = False
                break
        if valid:
            proposals.append(proposal)
    return proposals


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
    task = TaskTemplate(
        journey_stage_id=stage.id,
        title=payload.title,
        body_markdown=payload.instructions_markdown,
        required=payload.required,
        team_id=template.team_id,
    )
    session.add(task)
    await session.flush()

    for chunk in payload.source_chunks:
        section = await session.get(DocumentSection, chunk.document_section_id)
        if section is None:
            raise PortalError(422, "INVALID_SOURCE_CHUNK", "portal.invalid_source_chunk")
        version = await session.get(DocumentVersion, section.version_id)
        assert version is not None  # FK đảm bảo section luôn có version hợp lệ
        session.add(
            TaskSourceMapping(
                task_template_id=task.id,
                document_id=version.document_id,
                document_version_id=version.id,
                document_section_id=section.id,
            )
        )
    await session.commit()
    return task
