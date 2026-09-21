import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

// Trang khung. Giao diện đăng nhập (tái dùng từ Ralion) và nối API làm ở Phase 4.
export default function LoginPage() {
  const t = useTranslations("login");

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 px-4 py-16">
      <h1 className="text-ink text-[22px] font-bold">{t("title")}</h1>
      <p className="text-ink-2">{t("placeholder")}</p>
      <div>
        <Link href="/" className="text-accent hover:text-accent-hover underline">
          {t("back")}
        </Link>
      </div>
    </main>
  );
}
