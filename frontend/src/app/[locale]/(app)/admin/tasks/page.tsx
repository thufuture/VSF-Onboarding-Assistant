import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { TaskManagementPage } from "@/features/portal-hr/TaskManagementPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// "Quản lý task" thật (plan-portal) — xem/thêm/sửa/xóa task theo giai đoạn, GET /portal/journey-templates/mine.
export default async function AdminTasksPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  return <TaskManagementPage />;
}
