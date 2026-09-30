import { useTranslations } from "next-intl";
import type { MouseEventHandler } from "react";

import { VsfMark } from "@/components/brand/VsfMark";
import { Link } from "@/i18n/navigation";

import styles from "./VsfBrand.module.scss";

/**
 * Logo chữ của VSF Onboarding Assistant: biểu tượng chữ "V" trên ô bo góc, kèm tên "VSF Onboarding" (màu theo
 * `currentColor`, đổi được trên nền ảnh hoặc nền trắng) và "Assistant" màu đen, đậm hơn. Chưa dùng logo Vin/VSF vì chưa được
 * đồng ý (xem landing-page-plan.md mục 5).
 */
export function VsfBrand({
  href = "/",
  size = 26,
  stacked = false,
  onClick,
}: {
  href?: string;
  size?: number;
  /** Hai dòng: "VSF Onboarding" (màu --vsf-brand-primary) trên, "Assistant" (màu đen) dưới. */
  stacked?: boolean;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
}) {
  const t = useTranslations("landing.nav");

  return (
    <Link aria-label={t("brand")} className={`${styles.brand} ${stacked ? styles.stacked : ""}`} href={href} onClick={onClick}>
      <VsfMark className={styles.mark} size={size} />
      <span aria-hidden="true" className={styles.word} style={{ fontSize: Math.round(size * 0.62) }}>
        <span>VSF Onboarding</span>
        <span className={styles.accent}>Assistant</span>
      </span>
    </Link>
  );
}
