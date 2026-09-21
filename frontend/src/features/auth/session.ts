import type { LoginRequestDTO } from "@/features/auth/dto/requestDTO/auth.request";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import type { ErrorResponseDTO } from "@/types/apiError";

export type SessionErrorCode = "invalid_credentials" | "account_inactive" | "rate_limited" | "unavailable" | "network";

export class SessionError extends Error {
  readonly code: SessionErrorCode;

  constructor(code: SessionErrorCode) {
    super(code);
    this.name = "SessionError";
    this.code = code;
  }
}

/** Đọc mã lỗi ổn định của backend (`{code, message_key, detail}`); thân không phải JSON thì trả null. */
async function readErrorCode(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as Partial<ErrorResponseDTO>;
    return typeof body.code === "string" ? body.code : null;
  } catch {
    return null;
  }
}

/**
 * Phiên là cookie `vsf_session` do server đặt (httpOnly): frontend không giữ định danh nào và không gửi header
 * định danh tự chế.
 */
async function login(email: string, password: string): Promise<SessionUserResponseDTO> {
  const body: LoginRequestDTO = { email, password };
  let response: Response;
  try {
    response = await fetch("/api/v1/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new SessionError("network");
  }

  if (response.status === 401) throw new SessionError("invalid_credentials");
  if (response.status === 403) {
    // 403 khi đăng nhập là tài khoản bị khóa; mã khác (nếu có) coi như không khả dụng.
    throw new SessionError((await readErrorCode(response)) === "ACCOUNT_INACTIVE" ? "account_inactive" : "unavailable");
  }
  if (response.status === 429) throw new SessionError("rate_limited");
  if (!response.ok) throw new SessionError("unavailable");

  try {
    return (await response.json()) as SessionUserResponseDTO;
  } catch {
    throw new SessionError("unavailable");
  }
}

export const authApi = { login };
