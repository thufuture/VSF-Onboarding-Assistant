// Khớp GET /api/v1/portal/analytics (backend: analytics_response_dto.py). Danh sách `*_per_day` có đúng `dates.length` phần tử.

export type LabelCountResponseDTO = { key: string; count: number };

export type GroupTaskStateResponseDTO = { group: string; done: number; ready: number; locked: number };

export type OperationBreakdownResponseDTO = {
  operation: string;
  kind: string;
  calls: number;
  errors: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  input_count: number;
  cost_usd: number;
};

export type JobRunResponseDTO = {
  job_id: number;
  started_at: string | null;
  status: "SUCCEEDED" | "FAILED";
  duration_seconds: number | null;
  documents: number;
  items: number;
  llm_calls: number;
  llm_latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
};

export type PeopleAnalyticsResponseDTO = {
  employees_total: number;
  completion_percent: number;
  by_progress: LabelCountResponseDTO[];
  tasks_by_state: LabelCountResponseDTO[];
  tasks_by_group: GroupTaskStateResponseDTO[];
  completed_per_day: number[];
};

export type DocumentAnalyticsResponseDTO = {
  total: number;
  by_state: LabelCountResponseDTO[];
  by_category: LabelCountResponseDTO[];
};

export type VigaAnalyticsResponseDTO = {
  total_questions: number;
  questions_per_day: number[];
  by_outcome: LabelCountResponseDTO[];
  by_route: LabelCountResponseDTO[];
  no_llm_percent: number;
  answered_percent: number;
};

export type TicketAnalyticsResponseDTO = {
  by_status: LabelCountResponseDTO[];
  created_per_day: number[];
  open_gaps: number;
  avg_first_reply_hours: number | null;
};

export type AiAnalyticsResponseDTO = {
  calls: number;
  errors: number;
  cost_usd: number;
  calls_per_day: number[];
  errors_per_day: number[];
  cost_per_day: number[];
  by_operation: OperationBreakdownResponseDTO[];
  task_runs: JobRunResponseDTO[];
  activation_runs: JobRunResponseDTO[];
};

export type PortalAnalyticsResponseDTO = {
  days: number;
  dates: string[];
  scope: "TEAM" | "ALL";
  team_name: string | null;
  generated_at: string;
  people: PeopleAnalyticsResponseDTO;
  documents: DocumentAnalyticsResponseDTO;
  viga: VigaAnalyticsResponseDTO;
  tickets: TicketAnalyticsResponseDTO;
  ai: AiAnalyticsResponseDTO;
};
