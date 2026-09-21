import { getLocale } from "next-intl/server";

import { AdminPlaceholder } from "@/features/app-shell/AdminPlaceholder";
import { getSessionUser } from "@/features/auth/server";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Khu dành cho HR và Admin (trang giữ chỗ; màn hình quản lý làm ở Phase 5 đến 8). Nhân sự mới bị chuyển về chat.
export default async function AdminPage() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/chat", locale: (await getLocale()) as Locale });
  return <AdminPlaceholder />;
}
