import { useTranslations } from "next-intl";
import { useId, type MouseEventHandler } from "react";

import { Link } from "@/i18n/navigation";

import styles from "./VsfBrand.module.css";

/**
 * Logo chữ của VSF Onboarding Assistant: biểu tượng chữ "V" trên ô bo góc, kèm tên "VSF Onboarding" (màu theo
 * `currentColor`, đổi được trên nền ảnh hoặc nền trắng) và "Assistant" màu đen, đậm hơn. Chưa dùng logo Vin/VSF vì chưa được
 * đồng ý (xem landing-page-plan.md mục 5).
 */
export function VsfBrand({
  href = "/",
  size = 26,
  onClick,
}: {
  href?: string;
  size?: number;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
}) {
  const t = useTranslations("landing.nav");
  // Mỗi logo một id riêng: nhiều logo trên cùng trang (kể cả logo đang ẩn) không được dùng chung gradient.
  const gradientId = useId();

  return (
    <Link aria-label={t("brand")} className={styles.brand} href={href} onClick={onClick}>
      <svg aria-hidden="true" className={styles.mark} fill="none" height={size} viewBox="0 0 32 32" width={size}>
        <defs>
          <linearGradient id={gradientId} x1="4" x2="28" y1="2" y2="30" gradientUnits="userSpaceOnUse">
            <stop stopColor="#1aa5e0" />
            <stop offset="1" stopColor="#0a66a8" />
          </linearGradient>
        </defs>
        <rect fill={`url(#${gradientId})`} height="32" rx="9" width="32" />
        <path d="M8.5 9.5 16 23l7.5-13.5" stroke="#fff" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
      </svg>
      <span aria-hidden="true" className={styles.word} style={{ fontSize: Math.round(size * 0.62) }}>
        <span>VSF Onboarding</span>
        <span className={styles.accent}>Assistant</span>
      </span>
    </Link>
  );
}
