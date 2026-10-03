import type {
  AddTicketMessageRequestDTO,
  CreateTicketRequestDTO,
  SetTicketStatusRequestDTO,
  SupplementGapRequestDTO,
  TicketStatusDTO,
  VigaAskRequestDTO,
  VigaFeedbackRequestDTO,
} from "@/features/viga/dto/requestDTO/viga.request";
import type {
  ContentGapResponseDTO,
  ConversationDetailResponseDTO,
  ConversationResponseDTO,
  DissatisfiedGroupResponseDTO,
  RecheckGapResponseDTO,
  SatisfactionSummaryResponseDTO,
  SupplementGapResponseDTO,
  TicketDetailResponseDTO,
  TicketSummaryResponseDTO,
  VigaAnswerResponseDTO,
  VigaFeedbackSummaryDTO,
} from "@/features/viga/dto/responseDTO/viga.response";
import type { ErrorResponseDTO } from "@/types/apiError";

export type VigaErrorCode = "unauthorized" | "forbidden" | "throttled" | "unavailable" | "network";

export class VigaError extends Error {
  readonly code: VigaErrorCode;
  readonly apiCode: string | null;
  readonly retryAfter: number | null;

  constructor(code: VigaErrorCode, apiCode: string | null = null, retryAfter: number | null = null) {
    super(apiCode ?? code);
    this.name = "VigaError";
    this.code = code;
    this.apiCode = apiCode;
    this.retryAfter = retryAfter;
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

async function call(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(path, { credentials: "include", ...init });
  } catch {
    throw new VigaError("network");
  }
  if (response.status === 401) throw new VigaError("unauthorized");
  if (response.status === 403) throw new VigaError("forbidden", await readErrorCode(response));
  if (response.status === 429) {
    const wait = Number(response.headers.get("Retry-After"));
    throw new VigaError("throttled", await readErrorCode(response), Number.isFinite(wait) && wait > 0 ? wait : null);
  }
  if (!response.ok) throw new VigaError("unavailable", await readErrorCode(response));
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await call(path, init);
  try {
    return (await response.json()) as T;
  } catch {
    throw new VigaError("unavailable");
  }
}

const JSON_HEADERS = { "Content-Type": "application/json" };

function ask(body: VigaAskRequestDTO): Promise<VigaAnswerResponseDTO> {
  return json("/api/v1/viga/ask", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

function listConversations(): Promise<ConversationResponseDTO[]> {
  return json("/api/v1/viga/conversations");
}

function getConversation(id: number): Promise<ConversationDetailResponseDTO> {
  return json(`/api/v1/viga/conversations/${id}`);
}

function renameConversation(id: number, title: string): Promise<ConversationResponseDTO> {
  return json(`/api/v1/viga/conversations/${id}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify({ title }),
  });
}

async function deleteConversation(id: number): Promise<void> {
  await call(`/api/v1/viga/conversations/${id}`, { method: "DELETE" });
}

function createTicket(body: CreateTicketRequestDTO): Promise<TicketSummaryResponseDTO> {
  return json("/api/v1/portal/tickets", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
}

function listMyTickets(): Promise<TicketSummaryResponseDTO[]> {
  return json("/api/v1/portal/tickets/mine");
}

function listStaffTickets(status?: TicketStatusDTO): Promise<TicketSummaryResponseDTO[]> {
  return json(`/api/v1/portal/tickets${status ? `?status=${status}` : ""}`);
}

function getTicket(id: number): Promise<TicketDetailResponseDTO> {
  return json(`/api/v1/portal/tickets/${id}`);
}

function addTicketMessage(id: number, body: AddTicketMessageRequestDTO): Promise<TicketDetailResponseDTO> {
  return json(`/api/v1/portal/tickets/${id}/messages`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

function claimTicket(id: number): Promise<TicketDetailResponseDTO> {
  return json(`/api/v1/portal/tickets/${id}/claim`, { method: "POST" });
}

function setTicketStatus(id: number, body: SetTicketStatusRequestDTO): Promise<TicketDetailResponseDTO> {
  return json(`/api/v1/portal/tickets/${id}/status`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

function listContentGaps(includeResolved = false): Promise<ContentGapResponseDTO[]> {
  return json(`/api/v1/portal/content-gaps${includeResolved ? "?include_resolved=true" : ""}`);
}

async function resolveContentGap(id: number): Promise<void> {
  await call(`/api/v1/portal/content-gaps/${id}/resolve`, { method: "POST" });
}

function recheckContentGap(id: number): Promise<RecheckGapResponseDTO> {
  return json(`/api/v1/portal/content-gaps/${id}/recheck`, { method: "POST" });
}

function supplementContentGap(id: number, body: SupplementGapRequestDTO): Promise<SupplementGapResponseDTO> {
  return json(`/api/v1/portal/content-gaps/${id}/supplement`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

function listDissatisfied(includeResolved = false): Promise<DissatisfiedGroupResponseDTO[]> {
  return json(`/api/v1/portal/viga-feedback${includeResolved ? "?include_resolved=true" : ""}`);
}

async function resolveDissatisfied(id: number): Promise<void> {
  await call(`/api/v1/portal/viga-feedback/${id}/resolve`, { method: "POST" });
}

function feedbackSummary(): Promise<SatisfactionSummaryResponseDTO> {
  return json("/api/v1/portal/viga-feedback/summary");
}

/** 👍/👎 cho một câu trả lời (bấm lại để đổi). */
function rateAnswer(messageId: number, body: VigaFeedbackRequestDTO): Promise<VigaFeedbackSummaryDTO & { comment: string | null }> {
  return json(`/api/v1/viga/messages/${messageId}/feedback`, {
    method: "PUT",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
}

async function clearRating(messageId: number): Promise<void> {
  await call(`/api/v1/viga/messages/${messageId}/feedback`, { method: "DELETE" });
}

/** Ghi "việc vừa mở" để Viga hiểu "việc này" (không đổi trạng thái việc). Lỗi không được làm hỏng trang. */
async function markTaskOpened(employeeTaskId: number): Promise<void> {
  try {
    await call(`/api/v1/portal/me/tasks/${employeeTaskId}/opened`, { method: "POST" });
  } catch {
    /* ghi nhận phụ: bỏ qua lỗi */
  }
}

export const vigaApi = {
  ask,
  listConversations,
  getConversation,
  renameConversation,
  deleteConversation,
  createTicket,
  listMyTickets,
  listStaffTickets,
  getTicket,
  addTicketMessage,
  claimTicket,
  setTicketStatus,
  listContentGaps,
  resolveContentGap,
  recheckContentGap,
  supplementContentGap,
  listDissatisfied,
  resolveDissatisfied,
  feedbackSummary,
  rateAnswer,
  clearRating,
  markTaskOpened,
};
