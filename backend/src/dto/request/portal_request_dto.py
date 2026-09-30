"""DTO yêu cầu của `/api/v1/portal/*` (plan-portal/P4B/P4B.md mục 8)."""

from typing import Literal

from pydantic import BaseModel, Field


class CreateJourneyTemplateRequestDTO(BaseModel):
    code: str
    title: str
    description: str | None = None


class CreateJourneyStageRequestDTO(BaseModel):
    title: str
    sort_order: int = 0


class CreateAiTaskProposalRequestDTO(BaseModel):
    document_version_id: int


class AiTaskSourceChunkRequestDTO(BaseModel):
    document_section_id: int
    quote: str


class AcceptAiTaskProposalRequestDTO(BaseModel):
    title: str
    instructions_markdown: str
    required: bool = True
    source_chunks: list[AiTaskSourceChunkRequestDTO] = []


class CreateTaskManualRequestDTO(BaseModel):
    title: str
    body_markdown: str
    required: bool = True
    sort_order: int | None = None
    depends_on: list[int] = []
    task_group: Literal["PROFILE", "TRAINING", "DEVICE", "OFFICE"] | None = None


class UpdateTaskTemplateRequestDTO(BaseModel):
    title: str
    body_markdown: str
    required: bool = True
    journey_stage_id: int | None = None
    sort_order: int | None = None
    depends_on: list[int] | None = None
    task_group: Literal["PROFILE", "TRAINING", "DEVICE", "OFFICE"] | None = None


class UpdateDocumentRequestDTO(BaseModel):
    title: str
    category_slug: str


class SetDocumentStatusRequestDTO(BaseModel):
    status: Literal["ACTIVE", "ARCHIVED"]


class UpdateMyProfileRequestDTO(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class ChangeMyPasswordRequestDTO(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)
