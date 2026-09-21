import { defineRouting } from "next-intl/routing";

// Tiếng Việt (mặc định) và tiếng Anh; công tắc ngôn ngữ ở đầu landing và trang đăng nhập.
export const routing = defineRouting({
  locales: ["vi", "en"],
  defaultLocale: "vi",
  localePrefix: "always",
  localeDetection: false,
});

// proxy.ts gắn ngôn ngữ của URL vào header này cho request; request.ts và root layout đọc lại.
export const LOCALE_HEADER = "x-vsf-locale";

export type Locale = (typeof routing.locales)[number];

export function isLocale(value: string): value is Locale {
  return (routing.locales as readonly string[]).includes(value);
}

export function localeFromPathname(pathname: string): Locale | null {
  const segment = pathname.split("/")[1] ?? "";
  return isLocale(segment) ? segment : null;
}

export function stripLocale(pathname: string): string {
  const locale = localeFromPathname(pathname);
  if (!locale) return pathname || "/";
  const stripped = pathname.slice(locale.length + 1);
  return stripped || "/";
}
