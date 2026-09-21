import type { Metadata } from "next";
import { headers } from "next/headers";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { LOCALE_HEADER, isLocale, routing } from "@/i18n/routing";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metadata");
  return { title: t("title"), description: t("description") };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const requested = (await headers()).get(LOCALE_HEADER) ?? routing.defaultLocale;
  const locale = isLocale(requested) ? requested : routing.defaultLocale;

  return (
    <html lang={locale}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
