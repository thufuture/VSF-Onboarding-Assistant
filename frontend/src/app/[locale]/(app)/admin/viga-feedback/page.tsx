import { getLocale } from "next-intl/server";

import { getSessionUser } from "@/features/auth/server";
import { VigaFeedbackPage } from "@/features/viga/VigaFeedbackPage";
import { redirect } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

export default async function AdminVigaFeedbackPageRoute() {
  const user = await getSessionUser();
  if (user?.role === "USER") return redirect({ href: "/me", locale: (await getLocale()) as Locale });
  return <VigaFeedbackPage />;
}
