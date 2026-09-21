import type { Metadata } from "next";
import { headers } from "next/headers";
import { getTranslations } from "next-intl/server";
import { Be_Vietnam_Pro } from "next/font/google";
import type { ReactNode } from "react";

import { LOCALE_HEADER, isLocale, routing } from "@/i18n/routing";

import "./globals.css";

// Phông thiết kế cho landing và đăng nhập: có bộ ký tự tiếng Việt đầy đủ (Poppins của Ralion thiếu dấu).
// next/font tải về lúc build và tự host, trình duyệt không gọi Google Fonts khi chạy.
const landingFont = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-landing",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metadata");
  return { title: t("title"), description: t("description") };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const requested = (await headers()).get(LOCALE_HEADER) ?? routing.defaultLocale;
  const locale = isLocale(requested) ? requested : routing.defaultLocale;

  return (
    <html lang={locale}>
      <body className={`${landingFont.variable} min-h-screen`}>{children}</body>
    </html>
  );
}
