import type {
  AcceptAiTaskProposalRequestDTO,
  CreateAiTaskProposalRequestDTO,
  CreateJourneyStageRequestDTO,
  CreateJourneyTemplateRequestDTO,
  CreateTaskManualRequestDTO,
  SetDocumentStatusRequestDTO,
  UpdateDocumentRequestDTO,
  UpdateTaskTemplateRequestDTO,
} from "@/features/portal-hr/dto/requestDTO/portal.request";
import type {
  AiTaskProposalResponseDTO,
  DocumentCategoryResponseDTO,
  DocumentListItemResponseDTO,
  DocumentUploadResponseDTO,
  EmployeeDocumentResponseDTO,
  EmployeeJourneyResponseDTO,
  EmployeeProfileResponseDTO,
  EmployeeSummaryResponseDTO,
  EmployeeTaskResponseDTO,
  HrDashboardResponseDTO,
  JourneyStageResponseDTO,
  JourneyTemplateResponseDTO,
  StageOptionResponseDTO,
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

export const portalHrApi = {
  createJourneyTemplate,
  createJourneyStage,
  uploadDocument,
  proposeAiTasks,
  acceptAiTaskProposal,
  originalDocumentUrl,
  getMyJourney,
  getMyProfile,
  updateMyProfile,
  changeMyPassword,
  listMyDocuments,
  completeTask,
  getDashboard,
  listDocuments,
  listStageOptions,
  setDocumentStatus,
  listMyTemplates,
  createTaskManual,
  updateTaskTemplate,
  deleteTaskTemplate,
  listEmployees,
  listDocumentCategories,
  updateDocument,
  publishTemplate,
};
