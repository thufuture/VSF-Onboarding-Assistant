import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AdminUsersPage } from "@/features/portal-admin/AdminUsersPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Quản trị hệ thống — Người dùng. Chỉ ADMIN; vai trò khác về trang tổng quan của mình.
export default async function AdminUsersPageRoute() {
  const user = await getSessionUser();
  if (user?.role !== "ADMIN") return redirect({ href: "/admin", locale: (await getLocale()) as Locale });
  return <AdminUsersPage />;
}
