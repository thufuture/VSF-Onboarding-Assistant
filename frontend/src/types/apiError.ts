/** Hình dạng lỗi duy nhất của API (khớp `backend/src/dto/response/error_response_dto.py`). */
export type ErrorResponseDTO = {
  /** Mã ổn định để mã xử lý, ví dụ `INVALID_CREDENTIALS`, `TOO_MANY_ATTEMPTS`. */
  code: string;
  /** Khóa thông điệp để giao diện dịch, ví dụ `auth.invalid_credentials`. */
  message_key: string;
  detail: string | null;
};
