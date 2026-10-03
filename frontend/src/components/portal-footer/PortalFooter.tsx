"use client";

import { useTranslations } from "next-intl";

import { VsfMark } from "@/components/brand/VsfMark";

import styles from "./PortalFooter.module.scss";

/** Chân trang dùng chung cho khung HR/Admin và khung nhân viên mới: logo VSF, ghi chú, liên kết tĩnh, bản quyền. */
export function PortalFooter() {
  const t = useTranslations("app");
  return (
    <footer className={styles.footer}>
      <div className={styles.left}>
        <VsfMark className={styles.mark} size={28} />
        <div>
          <b>{t("footer.brand")}</b>
          <small>{t("footer.note")}</small>
        </div>
      </div>
      <nav aria-hidden="true" className={styles.links}>
        <span>{t("footer.help")}</span>
        <span>{t("footer.privacy")}</span>
        <span>{t("footer.terms")}</span>
        <span>{t("footer.contact")}</span>
      </nav>
      <div className={styles.right}>{t("footer.copy")}</div>
    </footer>
  );
}
