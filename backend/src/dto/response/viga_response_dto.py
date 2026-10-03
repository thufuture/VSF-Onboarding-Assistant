"""DTO phản hồi của `/api/v1/viga/*`, ticket và câu hỏi chưa trả lời được (mục 6.2, 15.5, 17)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

VigaResponseType = Literal[
    "ANSWER",
    "NO_BASIS",
    "OUT_OF_SCOPE",
    "NEXT_STEP",
    "PREREQUISITE_REQUIRED",
    "DAY_PLAN",
    "INFO",
    "NOT_IN_JOURNEY",
    "CLARIFY",
    "ERROR",
]


class VigaSourceResponseDTO(BaseModel):
    document_title: str
    version_label: str
    section_heading: str | None
    document_url: str
    version_id: int


class VigaClaimResponseDTO(BaseModel):
    question: str
    response_type: Literal["ANSWER", "NO_BASIS"]
    text: str | None = None
    quote: str | None = None
    source: VigaSourceResponseDTO | None = None


class VigaBlockingTaskResponseDTO(BaseModel):
    task_id: int
    title: str
    state: Literal["done", "ready", "locked"]


class VigaActionResponseDTO(BaseModel):
    type: Literal["OPEN_TASK", "OPEN_DAY"]
    title: str
    task_id: int | None = None
    stage_id: int | None = None


class VigaSourceRefResponseDTO(BaseModel):
    kind: Literal["TASK", "DAY"]
    title: str


class VigaAnswerResponseDTO(BaseModel):
    """Câu trả lời của Viga. `message_key` + `message_params` để giao diện dịch; `message` là bản tiếng Việt dự phòng."""

    conversation_id: int
    message_id: int
    new_conversation: bool
    response_type: VigaResponseType
    message: str
    message_key: str | None = None
    message_params: dict[str, str | int] = {}
    claims: list[VigaClaimResponseDTO] = []
    blocking_tasks: list[VigaBlockingTaskResponseDTO] = []
    suggested_actions: list[VigaActionResponseDTO] = []
    sources: list[VigaSourceRefResponseDTO] = []
    # Gợi ý nút "Gửi câu hỏi này cho HR" (NO_BASIS, OUT_OF_SCOPE, ERROR); Viga không tự tạo ticket.
    can_report_to_hr: bool = False
    # Ý tài liệu chưa quy định khi phần còn lại đã trả lời được (đường thoát PARTIAL).
    unanswered: list[str] = []
    assumed_task_title: str | None = None
    route: str = "NONE"


class ConversationResponseDTO(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class VigaFeedbackSummaryResponseDTO(BaseModel):
    rating: Literal["UP", "DOWN"]
    reason: str | None = None


class ConversationMessageResponseDTO(BaseModel):
    id: int
    role: Literal["USER", "ASSISTANT"]
    content: str
    response_type: str | None
    payload: dict[str, Any]
    created_at: datetime
    feedback: VigaFeedbackSummaryResponseDTO | None = None


class ConversationDetailResponseDTO(BaseModel):
    conversation: ConversationResponseDTO
    messages: list[ConversationMessageResponseDTO]


class TicketSummaryResponseDTO(BaseModel):
    id: int
    subject: str
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    source: Literal["MANUAL", "VIGA"]
    created_at: datetime
    updated_at: datetime
    requester_name: str
    requester_email: str
    team_name: str
    assigned_hr_name: str | None
    related_task_title: str | None
    message_count: int
    last_sender_is_staff: bool
    resolution_note: str | None


class TicketMessageResponseDTO(BaseModel):
    id: int
    sender_name: str
    sender_role: str
    body: str
    created_at: datetime
    mine: bool


class TicketDetailResponseDTO(BaseModel):
    ticket: TicketSummaryResponseDTO
    messages: list[TicketMessageResponseDTO]


class ContentGapResponseDTO(BaseModel):
    """Câu hỏi Viga chưa trả lời được, ẩn danh (không có tên người hỏi); câu giống nhau đã gom và đếm."""

    id: int
    question_text: str
    occurrences: int
    first_asked_at: datetime
    last_asked_at: datetime
    resolved: bool
    kind: Literal["NO_BASIS", "PARTIAL"] = "NO_BASIS"
    answer_excerpt: str | None = None
    resolved_document_title: str | None = None


class RecheckGapResponseDTO(BaseModel):
    """Kết quả hỏi lại một câu chưa trả lời được sau khi HR bổ sung tài liệu."""

    answered: bool
    message: str | None = None
    document_title: str | None = None
    section_heading: str | None = None
    quote: str | None = None
    closed: int = 0


class SupplementGapResponseDTO(BaseModel):
    """Bản "Hỏi đáp bổ sung" vừa tạo; `job_id` là việc nền kích hoạt (hỏi tiến độ ở `/portal/jobs/{job_id}`)."""

    document_id: int
    document_version_id: int
    version_label: str
    job_id: int


class VigaFeedbackResponseDTO(BaseModel):
    message_id: int
    rating: Literal["UP", "DOWN"]
    reason: str | None = None
    comment: str | None = None


class DissatisfiedGroupResponseDTO(BaseModel):
    """Câu hỏi bị 👎, ẩn danh (không có tên người đánh giá); câu giống nhau đã gom và đếm."""

    id: int
    question_text: str
    answer_excerpt: str
    occurrences: int
    reasons: list[str]
    comments: list[str]
    first_at: datetime
    last_at: datetime
    resolved: bool


class SatisfactionSummaryResponseDTO(BaseModel):
    up: int
    down: int
    open_down: int
    satisfaction_percent: int | None
