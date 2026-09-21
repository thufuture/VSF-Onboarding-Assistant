import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

// Biểu tượng trang trí (aria-hidden), vẽ bằng SVG nhúng để không thêm phụ thuộc.
const ICONS: Record<string, ReactNode> = {
  sources: <path d="M6 3h9l4 4v14H6V3Zm8 1.5V8h3.5M9 12h7M9 15h7M9 18h5" />,
  noGuess: <path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6l-8-3Zm-3 9 2.2 2.2L15.5 10" />,
  approved: (
    <path d="M10 14a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1 1m2 4a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1-1" />
  ),
};

export const FEATURE_KEYS = ["sources", "noGuess", "approved"] as const;

export function FeatureCards() {
  const t = useTranslations("landing.features");

  return (
    <section id="features" aria-labelledby="features-title" className="bg-surface-2 scroll-mt-16 px-4 py-16 sm:py-20">
      <div className="mx-auto max-w-5xl">
        <h2 id="features-title" className="text-ink text-2xl font-bold sm:text-3xl">
          {t("title")}
        </h2>
        <p className="text-ink-2 mt-2">{t("subtitle")}</p>
        <ul className="mt-8 grid gap-4 sm:grid-cols-3">
          {FEATURE_KEYS.map((key) => (
            <li key={key} className="border-border bg-surface flex flex-col gap-3 rounded-lg border p-5 shadow-sm">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="text-accent h-6 w-6"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {ICONS[key]}
              </svg>
              <h3 className="text-ink font-semibold">{t(`items.${key}.title`)}</h3>
              <p className="text-ink-2">{t(`items.${key}.body`)}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
