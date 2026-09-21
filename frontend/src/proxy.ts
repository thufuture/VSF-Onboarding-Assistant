import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_HEADER, isLocale, routing } from "@/i18n/routing";

/**
 * Chỉ xử lý ngôn ngữ: `/` → `/vi`, `/x` → `/vi/x`. Chưa có cổng đăng nhập (Phase 4 thêm cookie `vsf_session`).
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

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(LOCALE_HEADER, segment);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

// Bỏ qua /api (do backend/Caddy xử lý), tài nguyên Next và mọi đường dẫn có đuôi tệp.
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|.*\\..*).*)"],
};
