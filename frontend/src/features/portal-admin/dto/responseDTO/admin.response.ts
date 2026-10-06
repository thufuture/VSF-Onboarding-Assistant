export type AdminUserResponseDTO = {
  id: number;
  display_name: string;
  email: string;
  role: "USER" | "HR" | "ADMIN";
  status: "ACTIVE" | "INACTIVE";
  last_login_at: string | null;
  team_names: string[];
};

export type AdminUserSecretResponseDTO = {
  user: AdminUserResponseDTO;
  temporary_password: string;
};

export type AdminTeamResponseDTO = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  created_at: string;
  hr_names: string[];
  hr_user_ids: number[];
  employee_count: number;
  hr_count: number;
  journey_title: string | null;
  journey_version: number | null;
  journey_status: "DRAFT" | "PUBLISHED" | null;
};

export type AdminMembershipResponseDTO = {
  team_id: number;
  team_name: string;
  user_id: number;
  user_name: string;
  user_email: string;
  user_role: "USER" | "HR" | "ADMIN";
  team_role: "HR" | "EMPLOYEE";
  access: "ACTIVE" | "BLOCKED_USER" | "BLOCKED_TEAM";
  joined_at: string;
};

export type AdminAuditLogResponseDTO = {
  id: number;
  created_at: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  target: string | null;
};

export type AdminDashboardResponseDTO = {
  active_teams: number;
  archived_teams: number;
  hr_count: number;
  employee_count: number;
  employees_without_team: number;
  inactive_users: number;
  employees_by_team: [string, number][];
  recent_logs: AdminAuditLogResponseDTO[];
};

export type AdminTemplateOverviewResponseDTO = {
  shared_template_id: number | null;
  shared_title: string | null;
  shared_version: number | null;
  shared_status: string | null;
  shared_task_count: number;
  teams_using_copy: number;
  active_teams: number;
};

export type AdminOperationMetricsResponseDTO = {
  operation: string;
  kind: string;
  calls: number;
  errors: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  input_count: number;
  cost_usd: number;
};

export type AdminDailyCostResponseDTO = {
  day: string;
  calls: number;
  cost_usd: number;
};

/** Số liệu gọi LLM và embedding. Chỉ có số liệu, không có nội dung câu hỏi hay tài liệu. */
export type AdminMetricsResponseDTO = {
  days: number;
  since: string;
  calls: number;
  errors: number;
  cost_usd: number;
  operations: AdminOperationMetricsResponseDTO[];
  daily: AdminDailyCostResponseDTO[];
};
