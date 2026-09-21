import type { UserRoleDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { stripLocale } from "@/i18n/routing";

export type UserRole = UserRoleDTO;

const ORIGIN = "http://vsf.local";
const ADMIN_AREA = "/admin";

/**
 * Chỉ nhận đường dẫn nội bộ cho tham số `?next=` (chống chuyển hướng mở): loại `//evil.com`, `/\evil.com`,
 * `https://evil.com`, `javascript:`. Trả về đường dẫn đã bỏ tiền tố ngôn ngữ (router có ngôn ngữ tự thêm lại).
 */
export function internalPath(value: string | null | undefined): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return null;
  try {
    const url = new URL(value, ORIGIN);
    // Trình phân tích URL coi "\" như "/" và bỏ ký tự điều khiển, nên kiểm lại origin sau khi phân tích.
    if (url.origin !== ORIGIN) return null;
    return `${stripLocale(url.pathname)}${url.search}${url.hash}`;
  } catch {
    return null;
  }
}

function isAdminArea(pathname: string): boolean {
  return pathname === ADMIN_AREA || pathname.startsWith(`${ADMIN_AREA}/`);
}

/** Trang mặc định sau đăng nhập: nhân viên vào chat; HR và Admin vào khu quản trị. */
export function defaultLandingPath(role: UserRole): string {
  return role === "USER" ? "/chat" : ADMIN_AREA;
}

/** Đích sau đăng nhập: `?next=` chỉ được nhận khi là đường dẫn nội bộ hợp lệ với vai trò. */
export function resolvePostLoginPath(role: UserRole, requested: string | null | undefined): string {
  const candidate = internalPath(requested);
  if (!candidate) return defaultLandingPath(role);

  const pathname = new URL(candidate, ORIGIN).pathname;
  if (pathname === "/login") return defaultLandingPath(role);
  if (isAdminArea(pathname) && role === "USER") return defaultLandingPath(role);
  return candidate;
}
