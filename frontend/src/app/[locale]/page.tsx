import { LandingPage } from "@/features/landing/LandingPage";

// Landing tĩnh, chỉ tiếng Việt (bố cục chuyển thể từ landing của Ralion, ảnh nền Vincom Center Đồng Khởi).
// Nút "Bắt đầu hỏi" dẫn tới /vi/login. Chi tiết: docs/chatbot-vsf/plan/landing-page-plan.md.
export default function HomePage() {
  return <LandingPage />;
}
