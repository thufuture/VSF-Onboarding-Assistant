import { KeyIcon } from "@primer/octicons-react";
import { useTranslations } from "next-intl";
import { Suspense } from "react";

import { VsfBrand } from "@/components/brand/VsfBrand";
import { LoginForm } from "@/features/auth/LoginForm";
import styles from "@/features/auth/LoginPage.module.css";
import { Link } from "@/i18n/navigation";

const BENEFIT_KEYS = ["sources", "approved", "noGuess"] as const;

// Giao diện đăng nhập (bố cục chuyển thể từ trang đăng nhập của Ralion): kiểm nhập liệu và gọi
// POST /api/v1/auth/login. Backend xác thực làm ở Phase 4.
export default function LoginPage() {
  const t = useTranslations("login");
  const nav = useTranslations("landing.nav");

  return (
    <div className={styles.loginPage}>
      <header className={styles.header}>
        <nav aria-label={nav("label")} className={styles.nav}>
          <span className={styles.headerBrand}>
            <VsfBrand href="/" size={24} />
          </span>
          <div className={styles.navLinks}>
            <Link href="/">{nav("top")}</Link>
            <Link href="/#how">{nav("how")}</Link>
            <Link href="/#roles">{nav("roles")}</Link>
          </div>
        </nav>
      </header>

      <main className={styles.loginMain}>
        <section aria-labelledby="login-intro-title" className={styles.storyPanel}>
          <div aria-hidden="true" className={styles.storyGlow} />
          <div className={styles.storyContent}>
            <span className={styles.eyebrow}>{t("eyebrow")}</span>
            <h1 id="login-intro-title">{t("welcomeTitle")}</h1>
            <p>{t("welcomeDescription")}</p>
            <ul className={styles.benefits}>
              {BENEFIT_KEYS.map((key) => (
                <li key={key}>
                  <span aria-hidden="true">✓</span>
                  {t(`benefits.${key}`)}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="login-title" className={styles.formContent}>
          <div className={styles.formHeading}>
            <span className={styles.mobileBrand}>
              <VsfBrand size={26} />
            </span>
            <div className={styles.formTitleRow}>
              <span aria-hidden="true" className={styles.formTitleIcon}>
                <KeyIcon size={18} />
              </span>
              <h2 id="login-title">{t("title")}</h2>
            </div>
            <span>{t("subtitle")}</span>
          </div>
          <div className={styles.card}>
            {/* useSearchParams (?next=) trong LoginForm cần Suspense. */}
            <Suspense>
              <LoginForm />
            </Suspense>
          </div>
          <p className={styles.legal}>{t("note")}</p>
          <p className={styles.legal}>
            <Link href="/">{t("back")}</Link>
          </p>
        </section>
      </main>
    </div>
  );
}
