"use client";

import { SignOutIcon } from "@primer/octicons-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { VsfBrand } from "@/components/brand/VsfBrand";
import { LanguageSwitcher } from "@/components/i18n/LanguageSwitcher";
import { useSession } from "@/features/auth/SessionProvider";

import styles from "./AppHeader.module.scss";

/** Đầu trang của khu đã đăng nhập: logo, chọn ngôn ngữ, tên người dùng, vai trò và nút đăng xuất. */
export function AppHeader() {
  const t = useTranslations("app");
  const { user, logout } = useSession();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function signOut() {
    if (pending) return;
    setPending(true);
    setFailed(false);
    try {
      await logout();
    } catch {
      setFailed(true);
      setPending(false);
    }
  }

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <VsfBrand href={user.role === "USER" ? "/chat" : "/admin"} size={24} />
        <div className={styles.right}>
          <LanguageSwitcher />
          <div className={styles.user}>
            <span className={styles.name}>{user.display_name}</span>
            <span className={styles.role}>{t(`roles.${user.role}`)}</span>
          </div>
          <button className={styles.logout} disabled={pending} onClick={signOut} type="button">
            <SignOutIcon aria-hidden="true" size={16} />
            <span>{pending ? t("signingOut") : t("signOut")}</span>
          </button>
        </div>
      </div>
      {failed ? (
        <p className={styles.error} role="alert">
          {t("signOutFailed")}
        </p>
      ) : null}
    </header>
  );
}
