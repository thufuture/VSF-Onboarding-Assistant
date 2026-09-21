"use client";

import { useTranslations } from "next-intl";

import { useSession } from "@/features/auth/SessionProvider";
import { Link } from "@/i18n/navigation";

import styles from "./AdminPlaceholder.module.scss";

export function AdminPlaceholder() {
  const t = useTranslations("admin");
  const roles = useTranslations("app.roles");
  const { user } = useSession();

  return (
    <main className={styles.main}>
      <section className={styles.card}>
        <p className={styles.badge}>{roles(user.role)}</p>
        <h1>{t("title", { name: user.display_name })}</h1>
        <p>{t("description")}</p>
        <ul>
          {(["documents", "registry", "tickets"] as const).map((key) => (
            <li key={key}>{t(`upcoming.${key}`)}</li>
          ))}
        </ul>
        <Link className={styles.link} href="/chat">
          {t("openChat")}
        </Link>
      </section>
    </main>
  );
}
