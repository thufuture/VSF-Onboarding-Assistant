import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AdminTeamsPage } from "@/features/portal-admin/AdminTeamsPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Quản trị hệ thống — Phòng ban. Chỉ ADMIN; vai trò khác về trang tổng quan của mình.
export default async function AdminTeamsPageRoute() {
  const user = await getSessionUser();
  if (user?.role !== "ADMIN") return redirect({ href: "/admin", locale: (await getLocale()) as Locale });
  return <AdminTeamsPage />;
}
