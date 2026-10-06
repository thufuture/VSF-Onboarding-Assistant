import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { AdminAuditPage } from "@/features/portal-admin/AdminAuditPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Quản trị hệ thống — Nhật ký thay đổi. Chỉ ADMIN; vai trò khác về trang tổng quan của mình.
export default async function AdminAuditPageRoute() {
  const user = await getSessionUser();
  if (user?.role !== "ADMIN") return redirect({ href: "/admin", locale: (await getLocale()) as Locale });
  return <AdminAuditPage />;
}
