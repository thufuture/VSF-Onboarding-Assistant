"""Hình dạng lỗi duy nhất của API (system design mục 9): khớp `frontend/src/types/apiError.ts`."""

from pydantic import BaseModel


class ErrorResponseDTO(BaseModel):
    """Mã ổn định để mã xử lý, khóa thông điệp để giao diện dịch, chi tiết tùy chọn (không chứa dữ liệu nhạy cảm)."""

    code: str
    message_key: str
    detail: str | None = None
