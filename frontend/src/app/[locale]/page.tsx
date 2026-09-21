import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

// Trang khung của Phase 1. Landing đầy đủ (nếu làm) là Phase 10; trước đó trang này dẫn tới đăng nhập.
export default function HomePage() {
  const t = useTranslations("home");

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 px-4 py-16">
      <p className="text-ink-3 text-xs">{t("demoNote")}</p>
      <h1 className="text-ink text-[22px] font-bold">{t("title")}</h1>
      <p className="text-ink-2">{t("description")}</p>
      <div>
        <Link
          href="/login"
          className="bg-accent hover:bg-accent-hover inline-block rounded-md px-4 py-2 font-semibold text-white transition-colors"
        >
          {t("cta")}
        </Link>
      </div>
    </main>
  );
}
