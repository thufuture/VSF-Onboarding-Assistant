import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AiTasksPage } from "@/features/portal-hr/AiTasksPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// HR/ADMIN thật (plan-portal/P4B) — chọn tài liệu đã ingest, AI đề xuất task, duyệt vào giai đoạn.
export default async function AdminAiTasksPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/chat", locale: (await getLocale()) as Locale });
  return <AiTasksPage />;
}
