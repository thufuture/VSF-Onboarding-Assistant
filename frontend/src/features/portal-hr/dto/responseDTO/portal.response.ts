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

export type DocumentUploadResponseDTO = {
  document_id: number;
  document_version_id: number;
  section_count: number;
  chunk_count: number;
  created: boolean;
};

export type AiTaskSourceChunkResponseDTO = {
  document_section_id: number;
  quote: string;
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

export type EmployeeTaskResponseDTO = {
  id: number;
  task_template_id: number;
  title: string;
  body_markdown: string;
  required: boolean;
  stage_title: string;
  sort_order: number;
  status: EmployeeTaskStatusDTO;
  completed_at: string | null;
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
