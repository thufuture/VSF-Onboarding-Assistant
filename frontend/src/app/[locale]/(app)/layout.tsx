import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { AppHeader } from "@/features/app-shell/AppHeader";
import { SessionProvider } from "@/features/auth/SessionProvider";
import { getSessionUser } from "@/features/auth/server";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Khu cần đăng nhập: proxy đã chặn khi thiếu cookie; ở đây kiểm cookie thật với backend (chữ ký, hạn dùng, thu hồi).
export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await getSessionUser();
  if (!user) return redirect({ href: "/login", locale: (await getLocale()) as Locale });

  return (
    <SessionProvider initialUser={user}>
      <AppHeader />
      {children}
    </SessionProvider>
  );
}
