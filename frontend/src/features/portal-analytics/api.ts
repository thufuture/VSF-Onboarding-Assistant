import { PortalError } from "@/features/portal-hr/api";
import type { PortalAnalyticsResponseDTO } from "@/features/portal-analytics/dto/responseDTO/analytics.response";
import type { ErrorResponseDTO } from "@/types/apiError";

async function readErrorCode(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as Partial<ErrorResponseDTO>;
    return typeof body.code === "string" ? body.code : null;
  } catch {
    return null;
  }
}

async function getAnalytics(days: number): Promise<PortalAnalyticsResponseDTO> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/portal/analytics?days=${days}`, { credentials: "include" });
  } catch {
    throw new PortalError("network");
  }
  if (response.status === 401) throw new PortalError("unauthorized");
  if (response.status === 403) throw new PortalError("forbidden", await readErrorCode(response));
  if (!response.ok) throw new PortalError("unavailable", await readErrorCode(response));
  return (await response.json()) as PortalAnalyticsResponseDTO;
}

/** Số liệu trang Tổng quan (HR: phòng ban của mình; Admin: toàn hệ thống). */
export const analyticsApi = { getAnalytics };
