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
  // Vercel tự đóng gói; standalone làm bước onBuildComplete của Vercel lỗi thiếu *.nft.json.
  output: process.env.VERCEL ? undefined : "standalone",

  // Dev: cho phép mở bằng 127.0.0.1 (mặc định Next chặn tài nguyên từ origin này nên trang không hydrate, nút không chạy).
  allowedDevOrigins: ["127.0.0.1"],

  // Proxy rewrite (/api/* bên dưới) tự ngắt kết nối (ECONNRESET) nếu backend trả lời quá lâu; câu hỏi chat
  // nhiều ý (tách nhiều câu con, tìm kiếm + LLM song song) có thể mất >10s — nâng thời gian chờ để không bị
  // ngắt giữa chừng. Chỉ ảnh hưởng dev (production qua Caddy, không qua rewrite này).
  // Video đính kèm ticket tối đa 50 MB: nâng giới hạn thân yêu cầu qua proxy (mặc định 10 MB, vượt thì trả 500 trước khi tới backend).
  experimental: { proxyTimeout: 60_000, proxyClientMaxBodySize: "60mb" },

  /**
   * Đưa API về cùng origin với trang để cookie phiên là first-party — cả dev lẫn Vercel (nơi frontend
   * và backend AWS khác domain, rewrite server-to-server là cách duy nhất giữ cookie first-party mà không
   * phải viết lại auth sang CORS/cookie cross-site, xem docs/chatbot-vsf/plan/infrastructure/
   * trien-khai-aws-vercel.md mục 0).
   *
   * Trên VPS (Hetzner/AWS EC2 tự host cả frontend lẫn backend sau Caddy), Caddy chặn `/api/*` TRƯỚC khi
   * chạm tới container frontend — rewrite này không bao giờ được gọi tới trong trường hợp đó, nên bật luôn
   * ở mọi môi trường không gây hại gì, chỉ đơn giản hóa: không cần phân nhánh theo NODE_ENV nữa.
   */
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_UPSTREAM_URL}/api/:path*` }];
  },
};

export default withNextIntl(nextConfig);
