import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { ChatShell } from "@/features/chat/ChatShell";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Nhân viên (USER) có khu riêng ở `/me`; chat thật chỉ dành cho HR/Admin.
export default async function ChatPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  return <ChatShell />;
}
