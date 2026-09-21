import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/**
 * Backend mà Next chuyển `/api/*` tới. Chỉ đọc ở phía server (không có tiền tố NEXT_PUBLIC_)
 * nên URL này không bị nhúng vào bundle trình duyệt.
 */
const API_UPSTREAM_URL = process.env.API_UPSTREAM_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Cho image Docker ở Phase 1b: chỉ chép .next/standalone và static.
  output: "standalone",

  /**
   * Chỉ ở môi trường dev: đưa API về cùng origin với trang để cookie phiên là first-party.
   * Ở production việc này do Caddy đảm nhiệm (`/api/*` → backend, còn lại → frontend), nên không rewrite ở đây.
   */
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    return [{ source: "/api/:path*", destination: `${API_UPSTREAM_URL}/api/:path*` }];
  },
};

export default withNextIntl(nextConfig);
