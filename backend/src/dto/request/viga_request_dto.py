"""DTO yêu cầu của `/api/v1/viga/*` và `/api/v1/portal/tickets` (mục 6.2, 17)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VigaAskRequestDTO(BaseModel):
    """Giao diện chỉ gửi câu hỏi và `conversation_id`; backend tự biết "việc hiện tại" của người hỏi (không có `task_id`)."""

    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None
    # Ngày dùng để lọc hiệu lực tài liệu; mặc định hôm nay theo app_timezone.
    as_of: date | None = None

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question không được chỉ có khoảng trắng")
        return stripped


class VigaFeedbackRequestDTO(BaseModel):
    """Đánh giá một câu trả lời của Viga; lý do và ghi chú chỉ dùng cho 👎 và đều không bắt buộc."""

    rating: Literal["UP", "DOWN"]
    reason: Literal["WRONG", "MISSING", "UNCLEAR", "OFF_TOPIC"] | None = None
    comment: str | None = Field(default=None, max_length=500)


class SupplementGapRequestDTO(BaseModel):
    """HR viết câu trả lời đúng cho một câu Viga chưa trả lời được (thêm vào tài liệu "Hỏi đáp bổ sung" của phòng ban)."""

    answer: str = Field(min_length=5, max_length=3000)
    question: str | None = Field(default=None, max_length=300)  # mặc định lấy câu hỏi gốc; HR có thể sửa cho rõ nghĩa
    contact: str | None = Field(default=None, max_length=200)


class RenameConversationRequestDTO(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class CreateTicketRequestDTO(BaseModel):
    """Nhân viên đã xem và có thể sửa câu hỏi/ghi chú trước khi gửi."""

    question: str = Field(min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=1000)
    employee_task_id: int | None = None
    conversation_id: int | None = None
    attachment_ids: list[int] = Field(default_factory=list, max_length=5)


class AddTicketMessageRequestDTO(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=5)


class SetTicketStatusRequestDTO(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    resolution_note: str | None = Field(default=None, max_length=2000)
