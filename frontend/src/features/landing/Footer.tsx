import { useTranslations } from "next-intl";

export function Footer() {
  const t = useTranslations("landing.footer");

  return (
    <footer className="border-border border-t px-4 py-10">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 text-sm">
        <p className="text-ink font-semibold">{t("brand")}</p>
        <p className="text-ink-2">{t("demo")}</p>
        <p className="text-ink-2">
          {t("contactLabel")}:{" "}
          <a href={`mailto:${t("contact")}`} className="text-accent hover:text-accent-hover underline">
            {t("contact")}
          </a>
        </p>
        <p className="text-ink-3 text-xs">{t("copyright")}</p>
      </div>
    </footer>
  );
}
