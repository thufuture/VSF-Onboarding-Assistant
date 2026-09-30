import { PortalError } from "@/features/portal-hr/api";
import type {
  CreateMembershipRequestDTO,
  CreateTeamRequestDTO,
  CreateUserRequestDTO,
  UpdateTeamRequestDTO,
  UpdateUserRequestDTO,
} from "@/features/portal-admin/dto/requestDTO/admin.request";
import type {
  AdminAuditLogResponseDTO,
  AdminDashboardResponseDTO,
  AdminMembershipResponseDTO,
  AdminTeamResponseDTO,
  AdminTemplateOverviewResponseDTO,
  AdminUserResponseDTO,
  AdminUserSecretResponseDTO,
} from "@/features/portal-admin/dto/responseDTO/admin.response";
import type { ErrorResponseDTO } from "@/types/apiError";

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
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const base = "/api/v1/admin";

export const portalAdminApi = {
  getDashboard: () => request<AdminDashboardResponseDTO>(`${base}/dashboard`),
  listUsers: () => request<AdminUserResponseDTO[]>(`${base}/users`),
  createUser: (body: CreateUserRequestDTO) => send<AdminUserSecretResponseDTO>("POST", `${base}/users`, body),
  updateUser: (id: number, body: UpdateUserRequestDTO) =>
    send<AdminUserResponseDTO>("PATCH", `${base}/users/${id}`, body),
  resetPassword: (id: number) => send<AdminUserSecretResponseDTO>("POST", `${base}/users/${id}/reset-password`),
  setUserStatus: (id: number, status: "ACTIVE" | "INACTIVE") =>
    send<AdminUserResponseDTO>("PATCH", `${base}/users/${id}/status`, { status }),
  listTeams: () => request<AdminTeamResponseDTO[]>(`${base}/teams`),
  createTeam: (body: CreateTeamRequestDTO) => send<AdminTeamResponseDTO>("POST", `${base}/teams`, body),
  updateTeam: (id: number, body: UpdateTeamRequestDTO) =>
    send<AdminTeamResponseDTO>("PATCH", `${base}/teams/${id}`, body),
  setTeamStatus: (id: number, isActive: boolean) =>
    send<AdminTeamResponseDTO>("PATCH", `${base}/teams/${id}/status`, { is_active: isActive }),
  copyTemplate: (id: number) => send<AdminTeamResponseDTO>("POST", `${base}/teams/${id}/copy-template`),
  listMemberships: () => request<AdminMembershipResponseDTO[]>(`${base}/memberships`),
  addMembership: (body: CreateMembershipRequestDTO) => send<void>("POST", `${base}/memberships`, body),
  removeMembership: (teamId: number, userId: number) =>
    send<void>("DELETE", `${base}/memberships/${teamId}/${userId}`),
  getTemplateOverview: () => request<AdminTemplateOverviewResponseDTO>(`${base}/template-overview`),
  listAuditLogs: () => request<AdminAuditLogResponseDTO[]>(`${base}/audit-logs?limit=100`),
};
