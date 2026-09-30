import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { EmployeesPage } from "@/features/portal-hr/EmployeesPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// "Nhân viên" thật (plan-portal) — danh sách + tiến độ lộ trình, GET /portal/employees.
export default async function AdminEmployeesPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/chat", locale: (await getLocale()) as Locale });
  return <EmployeesPage />;
}
