"""DTO yêu cầu của `POST /api/v1/chat/ask`."""

from datetime import date

from pydantic import BaseModel, Field, field_validator


class ChatAskRequestDTO(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # Ngày dùng để lọc hiệu lực tài liệu (INV3); mặc định hôm nay theo app_timezone nếu không truyền.
    as_of: date | None = None

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        # min_length=1 vẫn cho qua chuỗi toàn khoảng trắng (độ dài > 0) — chặn ở đây, tránh tốn 1 lượt
        # rewrite_query cho input rác.
        stripped = value.strip()
        if not stripped:
            raise ValueError("question không được chỉ có khoảng trắng")
        return stripped
