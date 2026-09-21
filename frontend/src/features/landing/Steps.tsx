import { useTranslations } from "next-intl";

// Thứ tự hiển thị của năm bước; chữ nằm trong messages/vi.json (landing.steps.items.<khóa>).
export const STEP_KEYS = ["ask", "search", "answer", "clarify", "ticket"] as const;

export function Steps() {
  const t = useTranslations("landing.steps");

  return (
    <section id="how" aria-labelledby="how-title" className="scroll-mt-16 px-4 py-16 sm:py-20">
      <div className="mx-auto max-w-3xl">
        <h2 id="how-title" className="text-ink text-2xl font-bold sm:text-3xl">
          {t("title")}
        </h2>
        <p className="text-ink-2 mt-2">{t("subtitle")}</p>
        <ol className="mt-8 flex flex-col gap-4">
          {STEP_KEYS.map((key, index) => (
            <li key={key} className="border-border bg-surface flex gap-4 rounded-lg border p-4 shadow-sm">
              <span
                aria-hidden="true"
                className="bg-accent-bg text-accent flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
              >
                {index + 1}
              </span>
              <div>
                <h3 className="text-ink font-semibold">{t(`items.${key}.title`)}</h3>
                <p className="text-ink-2 mt-1">{t(`items.${key}.body`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
