"""DTO phản hồi của `/api/v1/portal/*` (nghiệp vụ nhân viên — plan-portal/P2/P2.md)."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

EmployeeTaskStatusDTO = Literal["LOCKED", "READY", "IN_PROGRESS", "WAITING_EXTERNAL", "BLOCKED", "DONE", "SKIPPED"]


class EmployeePrerequisiteResponseDTO(BaseModel):
    title: str
    done: bool


class TaskSourceResponseDTO(BaseModel):
    """Nguồn của task: tài liệu, mục và đoạn trích nguyên văn (nút "Nguồn"; thiếu `quote` thì chỉ tô cả mục)."""

    document_title: str
    version_label: str
    version_id: int
    document_url: str
    section_heading: str | None
    quote: str | None


class EmployeeTaskResponseDTO(BaseModel):
    id: int
    task_template_id: int | None  # việc mẫu đã sao chép (nguồn); None nếu việc không có nguồn mẫu
    title: str
    body_markdown: str
    required: bool
    stage_id: int
    stage_title: str
    stage_sort_order: int
    sort_order: int
    task_group: str | None
    status: EmployeeTaskStatusDTO
    completed_at: datetime | None
    prerequisites: list[EmployeePrerequisiteResponseDTO]
    sources: list[TaskSourceResponseDTO] = []
    # Mã thay đổi đang chờ nhân viên xem ("Có chỉnh sửa"); None nếu việc này không có thay đổi chờ.
    pending_change_id: int | None = None


class EmployeeJourneyResponseDTO(BaseModel):
    id: int
    journey_template_id: int
    journey_title: str
    started_at: datetime
    tasks: list[EmployeeTaskResponseDTO]


class EmployeeJourneyCreatedResponseDTO(BaseModel):
    journey_id: int
    created: bool  # False: nhân viên đã có lộ trình từ trước (không tạo lại)


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
    """Tải file chỉ tạo bản nháp (nhanh, chưa embedding); `job_id` có khi chọn "tải và kích hoạt luôn"."""

    document_id: int
    document_version_id: int
    created_document: bool
    reused: bool  # True = đã có bản cùng nhãn và cùng nội dung (idempotent), không tạo mới
    job_id: int | None
    # Chất lượng cấu trúc của file (mục 13): GOOD / MEDIUM / POOR kèm mã cảnh báo để giao diện nhắc HR.
    structure_quality: Literal["GOOD", "MEDIUM", "POOR"] | None = None
    structure_warnings: list[str] = []


class AiTaskSourceChunkResponseDTO(BaseModel):
    document_section_id: int
    quote: str
    heading: str | None = None  # tiêu đề mục chứa đoạn trích, để HR biết đoạn nằm ở đâu


class DocumentSectionResponseDTO(BaseModel):
    """Một mục của tài liệu, để HR đọc lại mục AI đã bỏ qua."""

    id: int
    heading: str | None
    content: str
    document_title: str
    version_label: str


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
    task_group: Literal["PROFILE", "TRAINING", "DEVICE", "OFFICE"] | None = None
    order: int | None = None  # thứ tự nên làm (1..n) trong tài liệu này
    prerequisites: list[str] = []  # tên các đề xuất khác phải xong trước (đã kiểm: có thật, nằm trước, không vòng)
    # Gợi ý riêng cho HR khi duyệt (không đưa vào nội dung task của nhân viên), vd. chi tiết nguồn có mà hướng dẫn chưa nhắc.
    review_notes: list[str] = []

    @field_validator("order", mode="before")
    @classmethod
    def _order_or_none(cls, value: object) -> int | None:
        try:
            return int(value) if value is not None else None  # type: ignore[call-overload]
        except (TypeError, ValueError):
            return None

    @field_validator("prerequisites", mode="before")
    @classmethod
    def _prerequisites_list(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


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
    current_version_label: str | None = None
    version_count: int = 0
    draft_count: int = 0
    processing_count: int = 0
    processing_version_ids: list[int] = []


class DocumentTaskRefResponseDTO(BaseModel):
    id: int
    title: str
    day_title: str
    version_status: str


class DocumentImpactResponseDTO(BaseModel):
    """Việc tắt hoặc xóa một tài liệu sẽ chạm tới những gì: task chỉ dựa vào nó, task còn có nguồn khác, bản sao đã giao nhân viên."""

    only_tasks: list[DocumentTaskRefResponseDTO]
    shared_tasks: list[DocumentTaskRefResponseDTO]
    employee_copies: int
    version_count: int
    processing: bool


class DocumentCategoryResponseDTO(BaseModel):
    slug: str
    name: str


class StageOptionResponseDTO(BaseModel):
    id: int
    journey_template_id: int
    title: str
    template_title: str
    draft_version_id: int | None = None  # bản nháp sẽ nhận task AI (chưa có thì tạo khi tạo task đầu tiên)
    draft_version_no: int | None = None
    applied_version_no: int | None = None


class TaskNodeResponseDTO(BaseModel):
    id: int
    journey_stage_id: int
    stage_version_id: int
    title: str
    body_markdown: str
    required: bool
    sort_order: int
    team_id: int | None
    depends_on: list[int]
    task_group: str | None
    sources: list[TaskSourceResponseDTO] = []


StageVersionStatusDTO = Literal["DRAFT", "APPLIED", "ARCHIVED"]


class VersionNodeResponseDTO(BaseModel):
    id: int
    version_no: int
    status: StageVersionStatusDTO
    note: str | None
    based_on_version_id: int | None
    applied_at: datetime | None
    created_at: datetime
    tasks: list[TaskNodeResponseDTO]


class StageNodeResponseDTO(BaseModel):
    id: int
    title: str
    sort_order: int
    tasks: list[TaskNodeResponseDTO]  # việc của bản hiển thị mặc định (đang áp dụng, không thì nháp mới nhất)
    versions: list[VersionNodeResponseDTO] = []
    default_version_id: int | None = None


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


class EmployeeProfileResponseDTO(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    department: str | None
    joined_at: datetime
    last_login_at: datetime | None
    journey_started_at: datetime | None
    tasks_total: int
    tasks_done: int
    required_total: int
    required_done: int


class EmployeeDocumentResponseDTO(BaseModel):
    id: int
    title: str
    category_name: str
    category_slug: str
    updated_at: datetime
    latest_version_id: int
    section_count: int


DocumentVersionStateDTO = Literal["DRAFT", "PROCESSING", "SCHEDULED", "CURRENT", "SUPERSEDED", "FAILED"]


class DocumentVersionResponseDTO(BaseModel):
    id: int
    version_label: str
    revision_no: int
    state: DocumentVersionStateDTO
    status: str
    effective_from: date | None
    effective_to: date | None
    source: str  # UPLOAD | EDITED
    parent_version_id: int | None
    original_filename: str
    uploaded_by_name: str | None
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None
    failure_reason: str | None
    section_count: int
    task_count: int
    structure_quality: Literal["GOOD", "MEDIUM", "POOR"] | None = None
    structure_warnings: list[str] = []
    ai_split: Literal["APPLIED", "SKIPPED"] | None = None


class DocumentVersionDetailResponseDTO(BaseModel):
    version: DocumentVersionResponseDTO
    document_id: int
    document_title: str
    markdown: str
    can_edit: bool


class JobResponseDTO(BaseModel):
    """Tiến độ một việc nền. Không chứa nội dung tài liệu (INV8); `error` chỉ có mã và mô tả ngắn."""

    id: int
    kind: str
    status: Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
    progress_percent: int
    stage: str | None
    result: dict[str, Any] | None
    error: str | None
    document_version_id: int | None
    created_at: datetime
    finished_at: datetime | None
    # Tiến độ theo bước (`jobs.progress`), giây đã chạy và số việc xếp trước (khi còn chờ). Chỉ mã bước và số, không nội dung.
    progress: dict[str, Any] | None = None
    started_at: datetime | None = None
    elapsed_seconds: int | None = None
    queue_ahead: int | None = None


class StageVersionResponseDTO(BaseModel):
    id: int
    journey_stage_id: int
    version_no: int
    status: StageVersionStatusDTO
    note: str | None
    based_on_version_id: int | None
    applied_at: datetime | None
    created_at: datetime
    task_count: int


class ApplyPreviewResponseDTO(BaseModel):
    """Xem trước khi áp dụng (không ghi gì): bao nhiêu việc đổi, thêm, bỏ và bao nhiêu nhân viên sẽ nhận thông báo."""

    modified: int
    added: int
    removed: int
    employee_count: int
    has_applied_before: bool


class ApplyResultResponseDTO(BaseModel):
    version: StageVersionResponseDTO
    notified_count: int


RolloutStateDTO = Literal["UNSEEN", "SEEN", "UPDATED", "KEPT_OLD", "SUPERSEDED"]


class RolloutRowResponseDTO(BaseModel):
    notice_id: int
    user_id: int
    display_name: str
    email: str
    state: RolloutStateDTO
    pending: int
    accepted: int
    dismissed: int
    total: int
    read_at: datetime | None


ChangeKindDTO = Literal["MODIFIED", "ADDED", "REMOVED", "PREREQUISITES"]
ChangeStatusDTO = Literal["PENDING", "ACCEPTED", "DISMISSED", "SUPERSEDED"]


class TaskChangeResponseDTO(BaseModel):
    """Một việc thay đổi: nội dung TRƯỚC (của chính nhân viên) và SAU (bản mới)."""

    id: int
    notice_id: int
    kind: ChangeKindDTO
    status: ChangeStatusDTO
    task_title: str
    employee_task_id: int | None
    employee_status: EmployeeTaskStatusDTO | None  # trạng thái hiện tại của việc (đã làm hay chưa)
    stage_title: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    changed_fields: list[str]
    informational: bool  # việc đã làm bị bỏ ở bản mới: giữ nguyên, chỉ báo thông tin (không có nút)


class JourneyNoticeResponseDTO(BaseModel):
    id: int
    journey_stage_id: int | None
    stage_title: str
    version_no: int
    created_at: datetime
    read_at: datetime | None
    changes: list[TaskChangeResponseDTO]


class ChangePreviewResponseDTO(BaseModel):
    """Hậu quả cụ thể của nút "Cập nhật" (hộp ghi chú trước khi bấm); không ghi gì."""

    change_id: int
    kind: ChangeKindDTO
    keeps_done: bool  # việc đã làm: cập nhật chỉ đổi nội dung, vẫn là đã xong
    removes_task: bool
    also_update: list[str]  # tên các việc được cập nhật kèm
    locked_until: list[str]  # việc sẽ bị khóa cho tới khi xong các việc này


class AcceptChangeResponseDTO(BaseModel):
    updated_change_ids: list[int]
