export type VigaResponseTypeDTO =
  | "ANSWER"
  | "NO_BASIS"
  | "OUT_OF_SCOPE"
  | "NEXT_STEP"
  | "PREREQUISITE_REQUIRED"
  | "DAY_PLAN"
  | "INFO"
  | "NOT_IN_JOURNEY"
  | "CLARIFY"
  | "ERROR";

export type VigaSourceResponseDTO = {
  document_title: string;
  version_label: string;
  section_heading: string | null;
  document_url: string;
  version_id: number;
};

export type VigaClaimResponseDTO = {
  question: string;
  response_type: "ANSWER" | "NO_BASIS";
  text: string | null;
  quote: string | null;
  source: VigaSourceResponseDTO | null;
};

export type VigaBlockingTaskResponseDTO = {
  task_id: number;
  title: string;
  state: "done" | "ready" | "locked";
};

export type VigaActionResponseDTO = {
  type: "OPEN_TASK" | "OPEN_DAY";
  title: string;
  task_id: number | null;
  stage_id: number | null;
};

export type VigaSourceRefResponseDTO = {
  kind: "TASK" | "DAY";
  title: string;
};

/** Câu trả lời của Viga. `message_key` + `message_params` để dịch theo ngôn ngữ đang chọn; `message` là bản tiếng Việt dự phòng. */
export type VigaAnswerResponseDTO = {
  conversation_id: number;
  message_id: number;
  new_conversation: boolean;
  response_type: VigaResponseTypeDTO;
  message: string;
  message_key: string | null;
  message_params: Record<string, string | number>;
  claims: VigaClaimResponseDTO[];
  blocking_tasks: VigaBlockingTaskResponseDTO[];
  suggested_actions: VigaActionResponseDTO[];
  sources: VigaSourceRefResponseDTO[];
  can_report_to_hr: boolean;
  /** Ý tài liệu chưa quy định khi các ý còn lại đã trả lời được (đường thoát PARTIAL). */
  unanswered?: string[];
  assumed_task_title: string | null;
  route: string;
  /** Đánh giá của chính người hỏi cho câu trả lời này (có khi mở lại hội thoại). */
  feedback?: VigaFeedbackSummaryDTO | null;
};

export type VigaFeedbackSummaryDTO = { rating: "UP" | "DOWN"; reason: string | null };

export type VigaFeedbackReasonDTO = "WRONG" | "MISSING" | "UNCLEAR" | "OFF_TOPIC";

export type ConversationResponseDTO = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ConversationMessageResponseDTO = {
  id: number;
  role: "USER" | "ASSISTANT";
  content: string;
  response_type: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  feedback?: VigaFeedbackSummaryDTO | null;
};

export type ConversationDetailResponseDTO = {
  conversation: ConversationResponseDTO;
  messages: ConversationMessageResponseDTO[];
};

export type TicketSummaryResponseDTO = {
  id: number;
  subject: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
  source: "MANUAL" | "VIGA";
  created_at: string;
  updated_at: string;
  requester_name: string;
  requester_email: string;
  team_name: string;
  assigned_hr_name: string | null;
  related_task_title: string | null;
  message_count: number;
  last_sender_is_staff: boolean;
  resolution_note: string | null;
};

export type TicketMessageResponseDTO = {
  id: number;
  sender_name: string;
  sender_role: string;
  body: string;
  created_at: string;
  mine: boolean;
};

export type TicketDetailResponseDTO = {
  ticket: TicketSummaryResponseDTO;
  messages: TicketMessageResponseDTO[];
};

/** Câu hỏi Viga chưa trả lời được, ẩn danh (không có tên người hỏi); câu giống nhau đã gom và đếm. */
export type ContentGapResponseDTO = {
  id: number;
  question_text: string;
  occurrences: number;
  first_asked_at: string;
  last_asked_at: string;
  resolved: boolean;
  /** NO_BASIS: cả câu không có căn cứ; PARTIAL: trả lời được một phần, phần còn lại tài liệu chưa quy định. */
  kind?: "NO_BASIS" | "PARTIAL";
  answer_excerpt?: string | null;
  resolved_document_title?: string | null;
};

/** Kết quả hỏi lại một câu sau khi HR bổ sung tài liệu. */
export type RecheckGapResponseDTO = {
  answered: boolean;
  message: string | null;
  document_title: string | null;
  section_heading: string | null;
  quote: string | null;
  closed: number;
};

export type SupplementGapResponseDTO = {
  document_id: number;
  document_version_id: number;
  version_label: string;
  job_id: number;
};

/** Câu hỏi nhân viên bấm 👎, ẩn danh; câu giống nhau đã gom và đếm. */
export type DissatisfiedGroupResponseDTO = {
  id: number;
  question_text: string;
  answer_excerpt: string;
  occurrences: number;
  reasons: string[];
  comments: string[];
  first_at: string;
  last_at: string;
  resolved: boolean;
};

export type SatisfactionSummaryResponseDTO = {
  up: number;
  down: number;
  open_down: number;
  satisfaction_percent: number | null;
};
