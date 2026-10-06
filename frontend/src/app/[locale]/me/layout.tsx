import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { SessionProvider } from "@/features/auth/SessionProvider";
import { getSessionUser } from "@/features/auth/server";
import { EmployeeShell } from "@/features/portal-employee/EmployeeShell";
import { JourneyProvider } from "@/features/portal-employee/JourneyProvider";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Khu của nhân viên mới (`/me`): cần đăng nhập, và chỉ dành cho vai trò USER — HR/Admin có khu quản trị riêng.
export default async function MeLayout({ children }: { children: ReactNode }) {
  const user = await getSessionUser();
  const locale = (await getLocale()) as Locale;
  if (!user) return redirect({ href: "/login", locale });
  if (user.role !== "USER") return redirect({ href: "/admin", locale });

  return (
    <SessionProvider initialUser={user}>
      <JourneyProvider>
        <EmployeeShell>{children}</EmployeeShell>
      </JourneyProvider>
    </SessionProvider>
  );
}
