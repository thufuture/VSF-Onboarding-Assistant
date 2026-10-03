"""DTO phản hồi của `GET /api/v1/portal/analytics`: số liệu cho trang Tổng quan (biểu đồ đường, cột, tròn, chi phí, độ trễ).

Mọi danh sách theo ngày (`*_per_day`) có đúng `len(dates)` phần tử, cùng thứ tự với `dates` (cũ trước mới sau), ngày không có
dữ liệu là 0. Chỉ có số liệu tổng hợp, không có nội dung câu hỏi, câu trả lời hay tài liệu (INV8); câu hỏi của từng người không lộ ra.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LabelCountResponseDTO(BaseModel):
    key: str
    count: int


class GroupTaskStateResponseDTO(BaseModel):
    group: str  # PROFILE | TRAINING | DEVICE | OFFICE | NONE
    done: int
    ready: int
    locked: int


class OperationBreakdownResponseDTO(BaseModel):
    operation: str
    kind: str
    calls: int
    errors: int
    p50_latency_ms: float
    p95_latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    input_count: int
    cost_usd: float


class JobRunResponseDTO(BaseModel):
    """Một lượt việc nền (tạo task bằng AI hoặc kích hoạt tài liệu): thời gian chạy thật, chi phí và độ trễ LLM cộng theo job."""

    job_id: int
    started_at: datetime | None
    status: Literal["SUCCEEDED", "FAILED"]
    duration_seconds: float | None
    documents: int
    items: int  # tạo task: số đề xuất; kích hoạt: số chunk đã ghi
    llm_calls: int
    llm_latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class PeopleAnalyticsResponseDTO(BaseModel):
    employees_total: int
    completion_percent: int
    by_progress: list[LabelCountResponseDTO]  # NO_JOURNEY, NOT_STARTED, IN_PROGRESS, COMPLETED
    tasks_by_state: list[LabelCountResponseDTO]  # done, ready, locked
    tasks_by_group: list[GroupTaskStateResponseDTO]
    completed_per_day: list[int]


class DocumentAnalyticsResponseDTO(BaseModel):
    total: int
    by_state: list[LabelCountResponseDTO]  # trạng thái hiển thị của từng phiên bản
    by_category: list[LabelCountResponseDTO]


class VigaAnalyticsResponseDTO(BaseModel):
    total_questions: int
    questions_per_day: list[int]
    by_outcome: list[LabelCountResponseDTO]  # response_type của câu trả lời
    by_route: list[LabelCountResponseDTO]  # SHORTCUT, GUARD, LLM, FALLBACK
    no_llm_percent: int  # câu trả lời không tốn LLM (lối tắt luật và bộ lọc)
    answered_percent: int  # câu có nội dung trả lời (không phải NO_BASIS, OUT_OF_SCOPE, ERROR)


class TicketAnalyticsResponseDTO(BaseModel):
    by_status: list[LabelCountResponseDTO]
    created_per_day: list[int]
    open_gaps: int
    avg_first_reply_hours: float | None


class AiAnalyticsResponseDTO(BaseModel):
    calls: int
    errors: int
    cost_usd: float
    calls_per_day: list[int]
    errors_per_day: list[int]
    cost_per_day: list[float]
    by_operation: list[OperationBreakdownResponseDTO]
    task_runs: list[JobRunResponseDTO]
    activation_runs: list[JobRunResponseDTO]


class PortalAnalyticsResponseDTO(BaseModel):
    days: int
    dates: list[str]  # ISO yyyy-mm-dd theo múi giờ ứng dụng
    scope: Literal["TEAM", "ALL"]
    team_name: str | None
    generated_at: datetime
    people: PeopleAnalyticsResponseDTO
    documents: DocumentAnalyticsResponseDTO
    viga: VigaAnalyticsResponseDTO
    tickets: TicketAnalyticsResponseDTO
    ai: AiAnalyticsResponseDTO
