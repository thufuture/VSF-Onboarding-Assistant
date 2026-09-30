import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AdminMembersPage } from "@/features/portal-admin/AdminMembersPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Quản trị hệ thống — Thành viên phòng ban. Chỉ ADMIN; vai trò khác về trang tổng quan của mình.
export default async function AdminMembersPageRoute() {
  const user = await getSessionUser();
  if (user?.role !== "ADMIN") return redirect({ href: "/admin", locale: (await getLocale()) as Locale });
  return <AdminMembersPage />;
}
