import type { UserRole } from "@/features/auth/routing";

/**
 * Người dùng hiện tại theo hợp đồng dự kiến của `POST /api/v1/auth/login` (Phase 4 hiện thực phía backend).
 * Phiên là cookie do server đặt; frontend không giữ định danh nào và không gửi header định danh tự chế.
 */
export type SessionUser = {
  id: number;
  email: string;
  display_name: string;
  role: UserRole;
};

export type SessionErrorCode = "invalid_credentials" | "rate_limited" | "unavailable" | "network";

export class SessionError extends Error {
  readonly code: SessionErrorCode;

  constructor(code: SessionErrorCode) {
    super(code);
    this.name = "SessionError";
    this.code = code;
  }
}

async function login(email: string, password: string): Promise<SessionUser> {
  let response: Response;
  try {
    response = await fetch("/api/v1/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new SessionError("network");
  }

  if (response.status === 401 || response.status === 403) throw new SessionError("invalid_credentials");
  if (response.status === 429) throw new SessionError("rate_limited");
  if (!response.ok) throw new SessionError("unavailable");

  try {
    return (await response.json()) as SessionUser;
  } catch {
    throw new SessionError("unavailable");
  }
}

export const authApi = { login };
