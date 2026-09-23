/** Phản hồi của `POST /api/v1/chat/ask` (khớp `backend/src/dto/response/chat_response_dto.py`).
 * `claims[]`: một câu hỏi của người dùng có thể tách thành nhiều ý độc lập, mỗi ý một claim riêng
 * (xem docs/chatbot-vsf/plan/phase-2/2-c-2-d-tim-kiem-va-tra-loi-ke-hoach-chi-tiet.md mục 6).
 */

export type SourceResponseDTO = {
  document_title: string;
  version_label: string;
  section_heading: string | null;
  /** URL Cloudinary mở được, hoặc đường dẫn cục bộ (dev/CI) không mở được — chỉ hiện thành link khi bắt đầu bằng "http". */
  document_url: string;
  /** Dùng để gọi `GET /api/v1/chat/documents/{version_id}` — hiện toàn bộ nội dung, cuộn tới đúng section. */
  version_id: number;
};

export type ClaimResponseDTO = {
  /** Câu hỏi con sau khi đã tách/viết lại — có thể khác nguyên văn câu người dùng gõ. */
  question: string;
  response_type: "ANSWER" | "NO_BASIS";
  reason_code: string | null;
  text: string | null;
  quote: string | null;
  source: SourceResponseDTO | null;
};

export type ChatAskResponseDTO = {
  claims: ClaimResponseDTO[];
};
