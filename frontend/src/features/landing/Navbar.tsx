import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

export function Navbar() {
  const t = useTranslations("landing.nav");

  return (
    <header className="border-border bg-surface/90 sticky top-0 z-10 border-b backdrop-blur">
      <nav aria-label={t("label")} className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="text-ink text-sm font-bold">
          {t("brand")}
        </Link>
        <div className="flex items-center gap-1 sm:gap-4">
          <a href="#how" className="text-ink-2 hover:text-ink hidden rounded-md px-2 py-1 text-sm sm:inline">
            {t("how")}
          </a>
          <a href="#features" className="text-ink-2 hover:text-ink hidden rounded-md px-2 py-1 text-sm sm:inline">
            {t("features")}
          </a>
          <Link
            href="/login"
            className="border-border-strong text-ink hover:bg-surface-2 rounded-md border px-3 py-1.5 text-sm font-semibold transition-colors"
          >
            {t("login")}
          </Link>
        </div>
      </nav>
    </header>
  );
}
