import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { DocumentsListPage } from "@/features/portal-hr/DocumentsListPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// HR/ADMIN thật (plan-portal/P4B) — danh sách tài liệu thật (GET /portal/documents) + upload.
export default async function AdminDocumentsPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  return <DocumentsListPage />;
}
