import { getSessionUser } from "@/features/auth/server";
import { ChatShell } from "@/features/chat/ChatShell";
import { RoadmapPage } from "@/features/portal-roadmap/RoadmapPage";

// Nhân viên (USER) thấy lộ trình onboarding (roadmap) ngay khi đăng nhập; HR/ADMIN vẫn thấy chat thật.
export default async function ChatPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return <RoadmapPage />;
  return <ChatShell />;
}
