import { getLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { getSessionUser } from "@/features/auth/server";
import { DocumentVersionsPage } from "@/features/portal-hr/DocumentVersionsPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Trang riêng của một tài liệu: phiên bản, so sánh, soạn thảo kiểu Word (thay cho cửa sổ nổi). Chỉ HR/ADMIN.
export default async function AdminDocumentVersionsPage({ params }: { params: Promise<{ documentId: string }> }) {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  const documentId = Number((await params).documentId);
  if (!Number.isInteger(documentId) || documentId <= 0) notFound();
  return <DocumentVersionsPage documentId={documentId} />;
}
