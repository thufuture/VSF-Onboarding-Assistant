import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { defaultLandingPath } from "@/features/auth/routing";
import { getSessionUser } from "@/features/auth/server";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

// Đã đăng nhập thì không cần thấy lại trang đăng nhập: chuyển tới trang mặc định của vai trò.
export default async function LoginLayout({ children }: { children: ReactNode }) {
  const user = await getSessionUser();
  if (user) redirect({ href: defaultLandingPath(user.role), locale: (await getLocale()) as Locale });
  return children;
}
