import { cookies } from "next/headers";
import { cache } from "react";

import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";

export const SESSION_COOKIE = "vsf_session";

// Backend mà server Next gọi trực tiếp (không qua trình duyệt); cùng biến với rewrite ở next.config.ts.
const API_UPSTREAM_URL = process.env.API_UPSTREAM_URL ?? "http://127.0.0.1:8000";

/**
 * Người dùng của yêu cầu hiện tại, hỏi backend bằng chính cookie của trình duyệt. Gọi nhiều lần trong một yêu cầu chỉ hỏi backend một lần. Trả `null` khi chưa đăng nhập,
 * cookie sai, hết hạn hay bị thu hồi; lỗi mạng cũng coi là chưa đăng nhập (không cho vào trang bảo vệ).
 */
export const getSessionUser = cache(async (): Promise<SessionUserResponseDTO | null> => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;

  try {
    const response = await fetch(`${API_UPSTREAM_URL}/api/v1/auth/me`, {
      headers: { Cookie: `${SESSION_COOKIE}=${token}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as SessionUserResponseDTO;
  } catch {
    return null;
  }
});
