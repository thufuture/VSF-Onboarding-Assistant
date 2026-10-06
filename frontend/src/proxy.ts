import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_HEADER, isLocale, routing, stripLocale } from "@/i18n/routing";

// Khu cần đăng nhập; đường dẫn không kèm tiền tố ngôn ngữ.
const PROTECTED_AREAS = ["/chat", "/admin", "/me"];
const SESSION_COOKIE = "vsf_session";

function isProtected(pathWithoutLocale: string): boolean {
  return PROTECTED_AREAS.some((area) => pathWithoutLocale === area || pathWithoutLocale.startsWith(`${area}/`));
}

/**
 * Ngôn ngữ: `/` → `/vi`, `/x` → `/vi/x`. Cổng đăng nhập: khu bảo vệ mà không có cookie `vsf_session` thì chuyển về
 * `/<ngôn ngữ>/login?next=`. Đây chỉ là chặn sớm (không nhấp nháy nội dung); chữ ký, hạn dùng và thu hồi do layout
 * của khu bảo vệ kiểm với backend (`/auth/me`).
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const segment = pathname.split("/")[1] ?? "";

  if (!isLocale(segment)) {
    const redirect = request.nextUrl.clone();
    redirect.pathname =
      pathname === "/" ? `/${routing.defaultLocale}` : `/${routing.defaultLocale}${pathname}`;
    return NextResponse.redirect(redirect);
  }

  const protectedArea = isProtected(stripLocale(pathname));
  if (protectedArea && !request.cookies.get(SESSION_COOKIE)?.value) {
    const login = request.nextUrl.clone();
    login.pathname = `/${segment}/login`;
    login.search = `?next=${encodeURIComponent(`${pathname}${request.nextUrl.search}`)}`;
    return NextResponse.redirect(login);
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(LOCALE_HEADER, segment);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  // Trang của người đã đăng nhập không được lưu trong bộ nhớ đệm của trình duyệt hay proxy.
  if (protectedArea) response.headers.set("Cache-Control", "no-store");
  return response;
}

// Bỏ qua /api (do backend/Caddy xử lý), tài nguyên Next và mọi đường dẫn có đuôi tệp.
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|.*\\..*).*)"],
};
