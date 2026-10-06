import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AdminDashboardPage } from "@/features/portal-admin/AdminDashboardPage";
import { HrDashboardPage } from "@/features/portal-hr/HrDashboardPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// ADMIN thấy tổng quan quản trị hệ thống; HR thấy tổng quan HR thật (GET /portal/dashboard).
export default async function AdminPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  if (user?.role === "ADMIN") return <AdminDashboardPage />;
  return <HrDashboardPage />;
}
