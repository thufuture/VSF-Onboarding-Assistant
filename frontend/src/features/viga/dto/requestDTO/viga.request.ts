export type VigaAskRequestDTO = {
  question: string;
  /** Chỉ gửi mã cuộc trò chuyện; backend tự đọc lịch sử và tự biết "việc hiện tại" của người hỏi. */
  conversation_id?: number | null;
};

export type VigaFeedbackRequestDTO = {
  rating: "UP" | "DOWN";
  reason?: "WRONG" | "MISSING" | "UNCLEAR" | "OFF_TOPIC" | null;
  comment?: string | null;
};

export type SupplementGapRequestDTO = {
  answer: string;
  question?: string | null;
  contact?: string | null;
};

export type RenameConversationRequestDTO = {
  title: string;
};

export type CreateTicketRequestDTO = {
  question: string;
  note?: string | null;
  employee_task_id?: number | null;
  conversation_id?: number | null;
};

export type AddTicketMessageRequestDTO = {
  body: string;
};

export type TicketStatusDTO = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";

export type SetTicketStatusRequestDTO = {
  status: TicketStatusDTO;
  resolution_note?: string | null;
};
