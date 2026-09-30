"""DTO phản hồi của `/api/v1/portal/*` (nghiệp vụ nhân viên — plan-portal/P2/P2.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EmployeeTaskStatusDTO = Literal["LOCKED", "READY", "IN_PROGRESS", "WAITING_EXTERNAL", "BLOCKED", "DONE", "SKIPPED"]


class EmployeeTaskResponseDTO(BaseModel):
    id: int
    task_template_id: int
    title: str
    body_markdown: str
    required: bool
    stage_title: str
    sort_order: int
    status: EmployeeTaskStatusDTO
    completed_at: datetime | None


class EmployeeJourneyResponseDTO(BaseModel):
    id: int
    journey_template_id: int
    journey_title: str
    started_at: datetime
    tasks: list[EmployeeTaskResponseDTO]


class JourneyTemplateResponseDTO(BaseModel):
    id: int
    code: str
    version: int
    title: str
    status: Literal["DRAFT", "PUBLISHED"]
    team_id: int | None


class JourneyStageResponseDTO(BaseModel):
    id: int
    journey_template_id: int
    title: str
    sort_order: int


class DocumentUploadResponseDTO(BaseModel):
    document_id: int
    document_version_id: int
    section_count: int
    chunk_count: int
    created: bool  # False = tài liệu cùng nội dung đã tồn tại (idempotent theo checksum)


class AiTaskSourceChunkResponseDTO(BaseModel):
    document_section_id: int
    quote: str


class AiTaskProposalResponseDTO(BaseModel):
    """Theo đúng contract v14 §14 — KHÔNG có `completion_mode` (P0A D1: mọi task chỉ tự-hoàn-thành)."""

    title: str
    summary: str
    instructions_markdown: str
    done_criteria: list[str]
    estimated_minutes: int | None
    source_chunks: list[AiTaskSourceChunkResponseDTO]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    warnings: list[str]


class TaskTemplateResponseDTO(BaseModel):
    id: int
    journey_stage_id: int
    title: str
    body_markdown: str
    required: bool
    team_id: int | None
    task_group: str | None


class HrDashboardResponseDTO(BaseModel):
    """KPI thật cho trang Tổng quan HR (không có link/publish-check vì chưa có mô hình đó)."""

    journey_template_count: int
    journey_stage_count: int
    task_template_count: int
    document_count: int


class DocumentListItemResponseDTO(BaseModel):
    id: int
    title: str
    category_name: str
    status: str
    updated_at: datetime
    latest_version_id: int | None
    section_count: int
    source_key: str | None
    category_slug: str
    owner_name: str | None
    task_titles: list[str]


class DocumentCategoryResponseDTO(BaseModel):
    slug: str
    name: str


class StageOptionResponseDTO(BaseModel):
    id: int
    journey_template_id: int
    title: str
    template_title: str


class TaskNodeResponseDTO(BaseModel):
    id: int
    journey_stage_id: int
    title: str
    body_markdown: str
    required: bool
    sort_order: int
    team_id: int | None
    depends_on: list[int]
    task_group: str | None


class StageNodeResponseDTO(BaseModel):
    id: int
    title: str
    sort_order: int
    tasks: list[TaskNodeResponseDTO]


class TemplateNodeResponseDTO(BaseModel):
    id: int
    code: str
    title: str
    status: Literal["DRAFT", "PUBLISHED"]
    team_id: int | None
    stages: list[StageNodeResponseDTO]


class EmployeeSummaryResponseDTO(BaseModel):
    id: int
    display_name: str
    email: str
    department: str | None
    journey_started: bool
    tasks_done: int
    tasks_total: int
    current_task_title: str | None
    current_stage_title: str | None
    current_status: EmployeeTaskStatusDTO | None
