export type JourneyTemplateResponseDTO = {
  id: number;
  code: string;
  version: number;
  title: string;
  status: "DRAFT" | "PUBLISHED";
  team_id: number | null;
};

export type JourneyStageResponseDTO = {
  id: number;
  journey_template_id: number;
  title: string;
  sort_order: number;
};

export type StructureQualityDTO = "GOOD" | "MEDIUM" | "POOR";

/** Tải file chỉ tạo bản nháp; `job_id` có khi chọn "tải và kích hoạt luôn" (xử lý nền, hỏi tiến độ ở /portal/jobs). */
export type DocumentUploadResponseDTO = {
  document_id: number;
  document_version_id: number;
  created_document: boolean;
  reused: boolean;
  job_id: number | null;
  structure_quality: StructureQualityDTO | null;
  structure_warnings: string[];
};

export type DocumentVersionStateDTO = "DRAFT" | "PROCESSING" | "SCHEDULED" | "CURRENT" | "SUPERSEDED" | "FAILED";

export type DocumentVersionResponseDTO = {
  id: number;
  version_label: string;
  revision_no: number;
  state: DocumentVersionStateDTO;
  status: string;
  effective_from: string | null;
  effective_to: string | null;
  source: "UPLOAD" | "EDITED";
  parent_version_id: number | null;
  original_filename: string;
  uploaded_by_name: string | null;
  created_at: string;
  updated_at: string;
  activated_at: string | null;
  failure_reason: string | null;
  section_count: number;
  task_count: number;
  structure_quality: StructureQualityDTO | null;
  structure_warnings: string[];
  ai_split: "APPLIED" | "SKIPPED" | null;
};

export type DocumentVersionDetailResponseDTO = {
  version: DocumentVersionResponseDTO;
  document_id: number;
  document_title: string;
  markdown: string;
  can_edit: boolean;
};

export type JobStatusDTO = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";

export type AiProposalDocumentResultDTO = {
  version_id: number;
  document_title: string;
  version_label: string;
  status: "DONE" | "FAILED";
  error?: string;
  proposals: AiTaskProposalResponseDTO[];
  truncated_sections?: number;
  /** Mục của tài liệu mà chưa task nào trích (đã được hỏi lại một lượt bổ sung). */
  uncovered_sections?: { section_id: number; heading: string | null }[];
};

/** Tiến độ một việc nền. Không chứa nội dung tài liệu; `error` chỉ có mã và mô tả ngắn. */
export type JobResponseDTO = {
  id: number;
  kind: "ACTIVATE_VERSION" | "AI_TASK_PROPOSAL" | string;
  status: JobStatusDTO;
  progress_percent: number;
  stage: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  document_version_id: number | null;
  created_at: string;
  finished_at: string | null;
};

export type AiTaskSourceChunkResponseDTO = {
  document_section_id: number;
  quote: string;
  heading?: string | null;
};

export type AiTaskProposalResponseDTO = {
  title: string;
  summary: string;
  instructions_markdown: string;
  done_criteria: string[];
  estimated_minutes: number | null;
  source_chunks: AiTaskSourceChunkResponseDTO[];
  confidence: "HIGH" | "MEDIUM" | "LOW";
  warnings: string[];
  task_group?: TaskGroupDTO | null;
  /** Thứ tự nên làm và tên các đề xuất phải xong trước. */
  order?: number | null;
  prerequisites?: string[];
  /** Gợi ý riêng cho HR khi duyệt (không đưa vào nội dung task của nhân viên). */
  review_notes?: string[];
};

export type TaskTemplateResponseDTO = {
  id: number;
  journey_stage_id: number;
  title: string;
  body_markdown: string;
  required: boolean;
  team_id: number | null;
};

export type EmployeeTaskStatusDTO =
  | "LOCKED"
  | "READY"
  | "IN_PROGRESS"
  | "WAITING_EXTERNAL"
  | "BLOCKED"
  | "DONE"
  | "SKIPPED";

export type EmployeePrerequisiteDTO = { title: string; done: boolean };

/** Nguồn của task: tài liệu, mục và đoạn trích nguyên văn (thiếu `quote` thì chỉ tô cả mục). */
export type TaskSourceDTO = {
  document_title: string;
  version_label: string;
  version_id: number;
  document_url: string;
  section_heading: string | null;
  quote: string | null;
};

export type EmployeeTaskResponseDTO = {
  id: number;
  task_template_id: number;
  title: string;
  body_markdown: string;
  required: boolean;
  stage_id: number;
  stage_title: string;
  stage_sort_order: number;
  sort_order: number;
  task_group: TaskGroupDTO | null;
  status: EmployeeTaskStatusDTO;
  completed_at: string | null;
  prerequisites: EmployeePrerequisiteDTO[];
  sources?: TaskSourceDTO[];
};

export type EmployeeProfileResponseDTO = {
  id: number;
  email: string;
  display_name: string;
  role: string;
  department: string | null;
  joined_at: string;
  last_login_at: string | null;
  journey_started_at: string | null;
  tasks_total: number;
  tasks_done: number;
  required_total: number;
  required_done: number;
};

export type EmployeeDocumentResponseDTO = {
  id: number;
  title: string;
  category_name: string;
  category_slug: string;
  updated_at: string;
  latest_version_id: number;
  section_count: number;
};

export type EmployeeJourneyResponseDTO = {
  id: number;
  journey_template_id: number;
  journey_title: string;
  started_at: string;
  tasks: EmployeeTaskResponseDTO[];
};

export type StageOptionResponseDTO = {
  id: number;
  journey_template_id: number;
  title: string;
  template_title: string;
};

export type HrDashboardResponseDTO = {
  journey_template_count: number;
  journey_stage_count: number;
  task_template_count: number;
  document_count: number;
};

export type DocumentListItemResponseDTO = {
  id: number;
  title: string;
  category_name: string;
  status: string;
  updated_at: string;
  latest_version_id: number | null;
  section_count: number;
  source_key: string | null;
  category_slug: string;
  owner_name: string | null;
  task_titles: string[];
  current_version_label: string | null;
  version_count: number;
  draft_count: number;
  processing_count: number;
  processing_version_ids: number[];
};

export type DocumentCategoryResponseDTO = {
  slug: string;
  name: string;
};

export type TaskGroupDTO = "PROFILE" | "TRAINING" | "DEVICE" | "OFFICE";

export type TaskNodeResponseDTO = {
  id: number;
  journey_stage_id: number;
  title: string;
  body_markdown: string;
  required: boolean;
  sort_order: number;
  team_id: number | null;
  depends_on: number[];
  task_group: TaskGroupDTO | null;
  sources?: TaskSourceDTO[];
};

export type StageNodeResponseDTO = {
  id: number;
  title: string;
  sort_order: number;
  tasks: TaskNodeResponseDTO[];
};

export type TemplateNodeResponseDTO = {
  id: number;
  code: string;
  title: string;
  status: "DRAFT" | "PUBLISHED";
  team_id: number | null;
  stages: StageNodeResponseDTO[];
};

export type EmployeeSummaryResponseDTO = {
  id: number;
  display_name: string;
  email: string;
  department: string | null;
  journey_started: boolean;
  tasks_done: number;
  tasks_total: number;
  current_task_title: string | null;
  current_stage_title: string | null;
  current_status: EmployeeTaskStatusDTO | null;
};
