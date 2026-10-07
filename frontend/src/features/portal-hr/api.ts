import type {
  AcceptAiTaskProposalRequestDTO,
  ActivateDocumentVersionRequestDTO,
  CopyDocumentVersionRequestDTO,
  CreateAiTaskProposalFromSectionsRequestDTO,
  CreateAiTaskProposalJobRequestDTO,
  CreateAiTaskProposalRequestDTO,
  CreateJourneyStageRequestDTO,
  CreateJourneyTemplateRequestDTO,
  CreateStageVersionRequestDTO,
  CreateTaskManualRequestDTO,
  DocumentTaskChoiceDTO,
  SetDocumentStatusRequestDTO,
  UpdateDocumentRequestDTO,
  UpdateDocumentVersionRequestDTO,
  UpdateTaskTemplateRequestDTO,
} from "@/features/portal-hr/dto/requestDTO/portal.request";
import type {
  AcceptChangeResponseDTO,
  AiTaskProposalResponseDTO,
  ApplyPreviewResponseDTO,
  ApplyResultResponseDTO,
  ChangePreviewResponseDTO,
  DocumentCategoryResponseDTO,
  DocumentImpactResponseDTO,
  DocumentListItemResponseDTO,
  DocumentUploadResponseDTO,
  DocumentVersionDetailResponseDTO,
  DocumentVersionResponseDTO,
  EmployeeDocumentResponseDTO,
  EmployeeJourneyCreatedResponseDTO,
  EmployeeJourneyResponseDTO,
  EmployeeProfileResponseDTO,
  EmployeeSummaryResponseDTO,
  EmployeeTaskResponseDTO,
  HrDashboardResponseDTO,
  JobResponseDTO,
  JourneyNoticeResponseDTO,
  JourneyStageResponseDTO,
  JourneyTemplateResponseDTO,
  RolloutRowResponseDTO,
  StageOptionResponseDTO,
  StageVersionResponseDTO,
  TaskTemplateResponseDTO,
  TemplateNodeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";
import type { ErrorResponseDTO } from "@/types/apiError";

export type PortalErrorCode = "unauthorized" | "forbidden" | "unavailable" | "network";

export class PortalError extends Error {
  readonly code: PortalErrorCode;
  readonly apiCode: string | null;

  constructor(code: PortalErrorCode, apiCode: string | null = null) {
    super(apiCode ?? code);
    this.name = "PortalError";
    this.code = code;
    this.apiCode = apiCode;
  }
}

async function readErrorCode(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as Partial<ErrorResponseDTO>;
    return typeof body.code === "string" ? body.code : null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { credentials: "include", ...init });
  } catch {
    throw new PortalError("network");
  }
  if (response.status === 401) throw new PortalError("unauthorized");
  if (response.status === 403) throw new PortalError("forbidden", await readErrorCode(response));
  if (!response.ok) throw new PortalError("unavailable", await readErrorCode(response));
  return (await response.json()) as T;
}

function createJourneyTemplate(body: CreateJourneyTemplateRequestDTO): Promise<JourneyTemplateResponseDTO> {
  return request("/api/v1/portal/journey-templates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function createJourneyStage(
  templateId: number,
  body: CreateJourneyStageRequestDTO,
): Promise<JourneyStageResponseDTO> {
  return request(`/api/v1/portal/journey-templates/${templateId}/stages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function uploadDocument(form: FormData): Promise<DocumentUploadResponseDTO> {
  return request("/api/v1/portal/documents", { method: "POST", body: form });
}

function proposeAiTasks(body: CreateAiTaskProposalRequestDTO): Promise<AiTaskProposalResponseDTO[]> {
  return request("/api/v1/portal/ai/task-proposals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function acceptAiTaskProposal(
  stageId: number,
  body: AcceptAiTaskProposalRequestDTO,
): Promise<TaskTemplateResponseDTO> {
  return request(`/api/v1/portal/stages/${stageId}/tasks/from-proposal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function originalDocumentUrl(versionId: number): string {
  return `/api/v1/portal/documents/${versionId}/original`;
}

function getMyJourney(): Promise<EmployeeJourneyResponseDTO> {
  return request("/api/v1/portal/me/journey");
}

/** HR thêm lộ trình cho một nhân viên trong team: sao chép các bản đang áp dụng, có hiệu lực ngay (idempotent). */
function createEmployeeJourney(userId: number): Promise<EmployeeJourneyCreatedResponseDTO> {
  return request(`/api/v1/portal/employees/${userId}/journey`, { method: "POST" });
}

/** Gọi điểm cuối trả 204 (không có thân): chỉ cần biết thành công hay lỗi nào. */
async function requestNoContent(path: string, init: RequestInit): Promise<void> {
  let response: Response;
  try {
    response = await fetch(path, { credentials: "include", ...init });
  } catch {
    throw new PortalError("network");
  }
  if (response.status === 401) throw new PortalError("unauthorized");
  if (response.status === 403) throw new PortalError("forbidden", await readErrorCode(response));
  if (!response.ok) throw new PortalError("unavailable", await readErrorCode(response));
}

// ── Phiên bản của từng ngày (HR) ──

function createStageVersion(stageId: number, body: CreateStageVersionRequestDTO = {}): Promise<StageVersionResponseDTO> {
  return request(`/api/v1/portal/stages/${stageId}/versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function updateStageVersionNote(versionId: number, note: string | null): Promise<StageVersionResponseDTO> {
  return request(`/api/v1/portal/stage-versions/${versionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
}

function deleteStageVersion(versionId: number): Promise<void> {
  return requestNoContent(`/api/v1/portal/stage-versions/${versionId}`, { method: "DELETE" });
}

function createTaskInVersion(versionId: number, body: CreateTaskManualRequestDTO): Promise<TaskTemplateResponseDTO> {
  return request(`/api/v1/portal/stage-versions/${versionId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function previewApplyVersion(versionId: number): Promise<ApplyPreviewResponseDTO> {
  return request(`/api/v1/portal/stage-versions/${versionId}/apply-preview`);
}

function applyStageVersion(versionId: number): Promise<ApplyResultResponseDTO> {
  return request(`/api/v1/portal/stage-versions/${versionId}/apply`, { method: "POST" });
}

function getVersionRollout(versionId: number): Promise<RolloutRowResponseDTO[]> {
  return request(`/api/v1/portal/stage-versions/${versionId}/rollout`);
}

// ── Thông báo thay đổi lộ trình (nhân viên) ──

function listMyJourneyNotices(): Promise<JourneyNoticeResponseDTO[]> {
  return request("/api/v1/portal/me/journey/notices");
}

function markJourneyNoticeRead(noticeId: number): Promise<void> {
  return requestNoContent(`/api/v1/portal/me/journey/notices/${noticeId}/read`, { method: "POST" });
}

function previewJourneyChange(changeId: number): Promise<ChangePreviewResponseDTO> {
  return request(`/api/v1/portal/me/journey/changes/${changeId}/preview`);
}

function acceptJourneyChange(changeId: number): Promise<AcceptChangeResponseDTO> {
  return request(`/api/v1/portal/me/journey/changes/${changeId}/accept`, { method: "POST" });
}

function acceptAllJourneyChanges(noticeId: number): Promise<AcceptChangeResponseDTO> {
  return request(`/api/v1/portal/me/journey/notices/${noticeId}/accept-all`, { method: "POST" });
}

function dismissJourneyChange(changeId: number): Promise<void> {
  return requestNoContent(`/api/v1/portal/me/journey/changes/${changeId}/dismiss`, { method: "POST" });
}

function completeTask(employeeTaskId: number): Promise<EmployeeTaskResponseDTO> {
  return request(`/api/v1/portal/me/tasks/${employeeTaskId}/complete`, { method: "POST" });
}

function getMyProfile(): Promise<EmployeeProfileResponseDTO> {
  return request("/api/v1/portal/me/profile");
}

function updateMyProfile(displayName: string): Promise<EmployeeProfileResponseDTO> {
  return request("/api/v1/portal/me/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });
}

async function changeMyPassword(currentPassword: string, newPassword: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/v1/portal/me/password", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  } catch {
    throw new PortalError("network");
  }
  if (response.status === 401) throw new PortalError("unauthorized");
  if (!response.ok) throw new PortalError("unavailable", await readErrorCode(response));
}

function listMyDocuments(): Promise<EmployeeDocumentResponseDTO[]> {
  return request("/api/v1/portal/me/documents");
}

function getDashboard(): Promise<HrDashboardResponseDTO> {
  return request("/api/v1/portal/dashboard");
}

function listDocuments(): Promise<DocumentListItemResponseDTO[]> {
  return request("/api/v1/portal/documents");
}

function listStageOptions(): Promise<StageOptionResponseDTO[]> {
  return request("/api/v1/portal/stages");
}

function setDocumentStatus(
  documentId: number,
  body: SetDocumentStatusRequestDTO,
): Promise<DocumentListItemResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function getDocumentImpact(documentId: number): Promise<DocumentImpactResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}/impact`);
}

function deleteDocument(documentId: number, tasks?: DocumentTaskChoiceDTO): Promise<void> {
  const query = tasks ? `?tasks=${tasks}` : "";
  return requestNoContent(`/api/v1/portal/documents/${documentId}${query}`, { method: "DELETE" });
}

function listMyTemplates(): Promise<TemplateNodeResponseDTO[]> {
  return request("/api/v1/portal/journey-templates/mine");
}

function createTaskManual(stageId: number, body: CreateTaskManualRequestDTO): Promise<TaskTemplateResponseDTO> {
  return request(`/api/v1/portal/stages/${stageId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function updateTaskTemplate(taskId: number, body: UpdateTaskTemplateRequestDTO): Promise<TaskTemplateResponseDTO> {
  return request(`/api/v1/portal/task-templates/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function deleteTaskTemplate(taskId: number): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/portal/task-templates/${taskId}`, { method: "DELETE", credentials: "include" });
  } catch {
    throw new PortalError("network");
  }
  if (response.status === 401) throw new PortalError("unauthorized");
  if (response.status === 403) throw new PortalError("forbidden", await readErrorCode(response));
  if (!response.ok) throw new PortalError("unavailable", await readErrorCode(response));
}

function listDocumentCategories(): Promise<DocumentCategoryResponseDTO[]> {
  return request("/api/v1/portal/document-categories");
}

function updateDocument(documentId: number, body: UpdateDocumentRequestDTO): Promise<DocumentListItemResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function publishTemplate(templateId: number): Promise<JourneyTemplateResponseDTO> {
  return request(`/api/v1/portal/journey-templates/${templateId}/publish`, { method: "POST" });
}

function listEmployees(): Promise<EmployeeSummaryResponseDTO[]> {
  return request("/api/v1/portal/employees");
}

const JSON_HEADERS = { "Content-Type": "application/json" };

function listDocumentVersions(documentId: number): Promise<DocumentVersionResponseDTO[]> {
  return request(`/api/v1/portal/documents/${documentId}/versions`);
}

function getDocumentVersion(documentId: number, versionId: number): Promise<DocumentVersionDetailResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}/versions/${versionId}`);
}

function copyDocumentVersion(
  documentId: number,
  versionId: number,
  body: CopyDocumentVersionRequestDTO = {},
): Promise<DocumentVersionResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}/versions/${versionId}/copy`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

function updateDocumentVersion(
  documentId: number,
  versionId: number,
  body: UpdateDocumentVersionRequestDTO,
): Promise<DocumentVersionResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}/versions/${versionId}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

async function deleteDocumentVersion(documentId: number, versionId: number): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/portal/documents/${documentId}/versions/${versionId}`, {
      method: "DELETE",
      credentials: "include",
    });
  } catch {
    throw new PortalError("network");
  }
  if (response.status === 401) throw new PortalError("unauthorized");
  if (response.status === 403) throw new PortalError("forbidden", await readErrorCode(response));
  if (!response.ok) throw new PortalError("unavailable", await readErrorCode(response));
}

function activateDocumentVersion(
  documentId: number,
  versionId: number,
  body: ActivateDocumentVersionRequestDTO = {},
): Promise<JobResponseDTO> {
  return request(`/api/v1/portal/documents/${documentId}/versions/${versionId}/activate`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

function getJob(jobId: number): Promise<JobResponseDTO> {
  return request(`/api/v1/portal/jobs/${jobId}`);
}

function listActiveJobs(kind?: string): Promise<JobResponseDTO[]> {
  const query = kind ? `&kind=${encodeURIComponent(kind)}` : "";
  return request(`/api/v1/portal/jobs?active=true${query}`);
}

function proposeAiTasksFromSections(
  body: CreateAiTaskProposalFromSectionsRequestDTO,
): Promise<AiTaskProposalResponseDTO[]> {
  return request("/api/v1/portal/ai/task-proposals/from-sections", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

function getDocumentSectionOrder(versionId: number): Promise<number[]> {
  return request(`/api/v1/portal/document-versions/${versionId}/section-order`);
}

function createAiTaskProposalJob(body: CreateAiTaskProposalJobRequestDTO): Promise<JobResponseDTO> {
  return request("/api/v1/portal/ai/task-proposal-jobs", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

export const portalHrApi = {
  createJourneyTemplate,
  createJourneyStage,
  uploadDocument,
  proposeAiTasks,
  acceptAiTaskProposal,
  originalDocumentUrl,
  getMyJourney,
  createEmployeeJourney,
  createStageVersion,
  updateStageVersionNote,
  deleteStageVersion,
  createTaskInVersion,
  previewApplyVersion,
  applyStageVersion,
  getVersionRollout,
  listMyJourneyNotices,
  markJourneyNoticeRead,
  previewJourneyChange,
  acceptJourneyChange,
  acceptAllJourneyChanges,
  dismissJourneyChange,
  getMyProfile,
  updateMyProfile,
  changeMyPassword,
  listMyDocuments,
  completeTask,
  getDashboard,
  listDocuments,
  listStageOptions,
  setDocumentStatus,
  getDocumentImpact,
  deleteDocument,
  listMyTemplates,
  createTaskManual,
  updateTaskTemplate,
  deleteTaskTemplate,
  listEmployees,
  listDocumentCategories,
  updateDocument,
  publishTemplate,
  listDocumentVersions,
  getDocumentVersion,
  copyDocumentVersion,
  updateDocumentVersion,
  deleteDocumentVersion,
  activateDocumentVersion,
  getJob,
  listActiveJobs,
  createAiTaskProposalJob,
  proposeAiTasksFromSections,
  getDocumentSectionOrder,
};
