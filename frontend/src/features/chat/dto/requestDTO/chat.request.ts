/** Yêu cầu của `POST /api/v1/chat/ask` (khớp `backend/src/dto/request/chat_request_dto.py`). */
export type ChatAskRequestDTO = {
  question: string;
  /** Ngày dùng để lọc hiệu lực tài liệu (ISO 8601, `YYYY-MM-DD`); bỏ trống thì backend dùng hôm nay. */
  as_of?: string;
};
