import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

export function Hero() {
  const t = useTranslations("landing.hero");

  return (
    <section className="from-accent-bg to-bg bg-gradient-to-b">
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-20 text-center sm:py-28">
        <p className="border-border bg-surface text-ink-2 rounded-full border px-3 py-1 text-xs font-medium">
          {t("demoBadge")}
        </p>
        <p className="text-accent text-sm font-semibold">{t("eyebrow")}</p>
        <h1 className="text-ink text-3xl font-bold tracking-tight text-balance sm:text-5xl">{t("title")}</h1>
        <p className="text-ink-2 max-w-2xl text-base text-pretty sm:text-lg">{t("description")}</p>
        <div className="flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="bg-accent hover:bg-accent-hover rounded-md px-5 py-2.5 font-semibold text-white transition-colors"
          >
            {t("primary")}
          </Link>
          <a
            href="#how"
            className="border-border-strong text-ink hover:bg-surface rounded-md border px-5 py-2.5 font-semibold transition-colors"
          >
            {t("secondary")}
          </a>
        </div>
        <p className="text-ink-3 text-xs">{t("note")}</p>
      </div>
    </section>
  );
}
