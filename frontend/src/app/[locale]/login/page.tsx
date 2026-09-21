import { useTranslations } from "next-intl";
import { Suspense } from "react";

import { LoginForm } from "@/features/auth/LoginForm";
import { Link } from "@/i18n/navigation";

// Thứ tự ba nguyên tắc ở panel trái; chữ nằm trong messages/vi.json (login.panel.items.<khóa>).
const PANEL_KEYS = ["sources", "noGuess", "approved"] as const;

// Giao diện đăng nhập (vỏ): kiểm nhập liệu và gọi POST /api/v1/auth/login. Backend xác thực làm ở Phase 4.
export default function LoginPage() {
  const t = useTranslations("login");

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="from-accent-bg to-surface-2 hidden flex-col justify-center gap-6 bg-gradient-to-br px-8 py-12 min-[680px]:flex lg:px-16">
        <h2 className="text-ink max-w-md text-2xl font-bold text-balance sm:text-3xl">{t("panel.title")}</h2>
        <ul className="flex max-w-md flex-col gap-4">
          {PANEL_KEYS.map((key) => (
            <li key={key} className="border-border bg-surface rounded-lg border p-4 shadow-sm">
              <h3 className="text-ink font-semibold">{t(`panel.items.${key}.title`)}</h3>
              <p className="text-ink-2 mt-1">{t(`panel.items.${key}.body`)}</p>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex flex-col justify-center px-4 py-12 sm:px-8">
        <div className="mx-auto flex w-full max-w-sm flex-col gap-6">
          <header className="flex flex-col gap-1">
            <p className="text-ink text-sm font-bold">{t("brand")}</p>
            <p className="text-ink-3 text-xs">{t("demoBadge")}</p>
          </header>

          <div className="border-border bg-surface flex flex-col gap-5 rounded-lg border p-6 shadow-md">
            <div className="flex flex-col gap-1">
              <h1 className="text-ink text-[22px] font-bold">{t("title")}</h1>
              <p className="text-ink-2">{t("subtitle")}</p>
            </div>
            {/* useSearchParams (?next=) trong LoginForm cần Suspense. */}
            <Suspense>
              <LoginForm />
            </Suspense>
            <p className="text-ink-3 text-xs">{t("note")}</p>
          </div>

          <Link href="/" className="text-accent hover:text-accent-hover text-sm underline">
            {t("back")}
          </Link>
        </div>
      </main>
    </div>
  );
}
