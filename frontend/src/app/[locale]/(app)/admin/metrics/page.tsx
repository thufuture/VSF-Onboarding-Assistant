import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AdminMetricsPage } from "@/features/portal-admin/AdminMetricsPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Quản trị hệ thống — Chi phí và hiệu năng AI. Chỉ ADMIN; vai trò khác về trang tổng quan của mình.
export default async function AdminMetricsRoute() {
  const user = await getSessionUser();
  if (user?.role !== "ADMIN") return redirect({ href: "/admin", locale: (await getLocale()) as Locale });
  return <AdminMetricsPage />;
}
