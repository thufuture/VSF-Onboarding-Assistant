import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { HrTicketsPage } from "@/features/viga/HrTicketsPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

export default async function AdminHrTicketsPageRoute() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  return <HrTicketsPage />;
}
