"use client";

import { ArrowRight } from "lucide-react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Link } from "@/i18n/navigation";

import styles from "./RolesFlow.module.scss";

const ROLE_KEYS = ["asker", "hr", "team", "admin"] as const;
type RoleKey = (typeof ROLE_KEYS)[number];

/**
 * Khối "Giá trị cho từng vai trò": thẻ ảnh bên trái hiện nội dung vai trò đang chọn, các ô hình thoi bên phải để chọn
 * vai trò (bố cục lấy cảm hứng từ phần "gọn trong năm bước" của VLearn). Ô đỏ cuối cùng chỉ là câu chốt của khối.
 */
export function RolesFlow() {
  const t = useTranslations("landing.roles");
  const [active, setActive] = useState<RoleKey>("asker");

  return (
    <section aria-labelledby="roles-title" className={styles.section} id="roles">
      <header className={styles.header}>
        <h2 id="roles-title">
          {t("titleStart")} <span className={styles.accent}>{t("titleAccent")}</span>
        </h2>
        <p>{t("lead")}</p>
      </header>

      <div className={styles.stage}>
        <article aria-live="polite" className={styles.card}>
          <Image
            alt=""
            className={styles.cardPhoto}
            fill
            sizes="(max-width: 1000px) 100vw, 520px"
            src="/images/landing/roles-vincom-facade.webp"
          />
          <div aria-hidden="true" className={styles.cardShade} />
          <div className={styles.cardBody}>
            <span className={styles.cardTag}>{t(`${active}.tag`)}</span>
            <h3>{t(`${active}.title`)}</h3>
            <p>{t(`${active}.body`)}</p>
            <Link className={styles.cardCta} href="/login">
              {t(`${active}.cta`)} <ArrowRight size={16} />
            </Link>
          </div>
        </article>

        <div aria-label={t("flow")} className={styles.diamonds} role="group">
          {ROLE_KEYS.map((key, index) => (
            <button
              aria-pressed={active === key}
              className={`${styles.tile} ${styles[`tile${index + 1}` as "tile1"]} ${active === key ? styles.tileActive : ""}`}
              key={key}
              onClick={() => setActive(key)}
              onFocus={() => setActive(key)}
              onMouseEnter={() => setActive(key)}
              type="button"
            >
              <span className={styles.tileNum}>{String(index + 1).padStart(2, "0")}</span>
              <span className={styles.tileTitle}>{t(`${key}.title`)}</span>
            </button>
          ))}
          <div className={`${styles.tile} ${styles.tile5} ${styles.tileRed}`}>
            <span className={styles.tileTitle}>{t("flow")}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
