"""DTO yêu cầu của `/api/v1/portal/*` (plan-portal/P4B/P4B.md mục 8)."""

from datetime import date, datetime
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
    # Các trường tách riêng từ đề xuất để ghép thành ba mục "Vì sao / Điều kiện hoàn thành / Các bước" (có thể bỏ trống).
    summary: str | None = None
    done_criteria: list[str] = []
    estimated_minutes: int | None = None
    warnings: list[str] = []
    task_group: Literal["PROFILE", "TRAINING", "DEVICE", "OFFICE"] | None = None
    depends_on: list[int] = []  # id các task đã tạo trước đó trong cùng bản nháp (giao diện đổi từ tên tiên quyết)
    # Bản nháp của ngày sẽ nhận task; bỏ trống = bản nháp mới nhất của ngày (chưa có thì tạo từ bản đang áp dụng).
    stage_version_id: int | None = None


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


class CopyDocumentVersionRequestDTO(BaseModel):
    label: str | None = Field(default=None, max_length=32)


class UpdateDocumentVersionRequestDTO(BaseModel):
    """Sửa bản nháp. `expected_updated_at` là khóa lạc quan: phải bằng `updated_at` lần đọc gần nhất."""

    expected_updated_at: datetime
    markdown: str | None = None
    label: str | None = Field(default=None, max_length=32)
    effective_from: date | None = None
    clear_effective_from: bool = False


class ActivateDocumentVersionRequestDTO(BaseModel):
    effective_from: date | None = None


class CreateAiTaskProposalJobRequestDTO(BaseModel):
    document_version_ids: list[int] = Field(min_length=1, max_length=20)


class CreateStageVersionRequestDTO(BaseModel):
    """Tạo bản nháp mới của một ngày, sao chép từ `from_version_id` (bỏ trống = bản đang áp dụng)."""

    from_version_id: int | None = None
    note: str | None = None


class UpdateStageVersionRequestDTO(BaseModel):
    note: str | None = None
