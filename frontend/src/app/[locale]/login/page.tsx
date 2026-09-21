import { MailIcon } from "@primer/octicons-react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { Suspense } from "react";

import { VsfBrand } from "@/components/brand/VsfBrand";
import { LanguageSwitcher } from "@/components/i18n/LanguageSwitcher";
import { LoginForm } from "@/features/auth/LoginForm";
import styles from "@/features/auth/LoginPage.module.scss";
import { Link } from "@/i18n/navigation";

const BENEFIT_KEYS = ["sources", "approved", "noGuess"] as const;

// Giao diện đăng nhập: ảnh nền toàn khung, chữ giới thiệu bên trái, thẻ đăng nhập bên phải. Kiểm nhập liệu ở client
// và gọi POST /api/v1/auth/login; backend xác thực làm ở Phase 4.
export default function LoginPage() {
  const t = useTranslations("login");
  const nav = useTranslations("landing.nav");
  const footer = useTranslations("landing.footer");

  return (
    <div className={styles.page}>
      <Image
        alt=""
        className={styles.bg}
        fill
        priority
        sizes="100vw"
        src="/images/landing/hero-vincom-dong-khoi.webp"
      />
      <div aria-hidden="true" className={styles.veil} />

      <header className={styles.top}>
        <nav aria-label={nav("label")} className={styles.topNav}>
          <span className={styles.brand}>
            <VsfBrand href="/" size={28} />
          </span>
          <LanguageSwitcher />
        </nav>
      </header>

      <main className={styles.main}>
        <section aria-labelledby="login-intro-title" className={styles.story}>
          <h1 id="login-intro-title">
            <span>{t("welcomeLine1")}</span>
            <span>{t("welcomeLine2")}</span>
          </h1>
          <p>{t("welcomeDescription")}</p>
          <ul className={styles.benefits}>
            {BENEFIT_KEYS.map((key) => (
              <li key={key}>
                <span aria-hidden="true">✓</span>
                {t(`benefits.${key}`)}
              </li>
            ))}
          </ul>
          <blockquote className={styles.quote}>{t("quote")}</blockquote>
        </section>

        <section aria-labelledby="login-title" className={styles.cardWrap}>
          <div className={styles.card}>
            <h2 id="login-title">{t("title")}</h2>
            <p className={styles.subtitle}>{t("subtitle")}</p>
            {/* useSearchParams (?next=) trong LoginForm cần Suspense. */}
            <Suspense>
              <LoginForm />
            </Suspense>
            <div className={styles.cardFoot}>
              <details className={styles.firstTime}>
                <summary>{t("firstTime")}</summary>
                <p>{t("note")}</p>
              </details>
              <a className={styles.support} href={`mailto:${footer("email")}`}>
                <MailIcon aria-hidden="true" size={14} />
                {t("support")}
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.bottom}>
        <span>{footer("copyright")}</span>
        <Link href="/">{t("back")}</Link>
      </footer>
    </div>
  );
}
