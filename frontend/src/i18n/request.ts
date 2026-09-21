import { headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";

import { LOCALE_HEADER, isLocale, routing } from "./routing";

// Không có header (ví dụ chạy ngoài proxy) thì dùng ngôn ngữ mặc định.
export default getRequestConfig(async () => {
  const requested = (await headers()).get(LOCALE_HEADER) ?? routing.defaultLocale;
  const locale = isLocale(requested) ? requested : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
