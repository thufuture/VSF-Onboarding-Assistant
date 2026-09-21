import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

/**
 * Nhãn thương hiệu dạng chữ + biểu tượng bong bóng chat vẽ bằng SVG. Chưa dùng logo Vin/VSF vì chưa được đồng ý
 * (xem landing-page-plan.md mục 5). Màu theo `currentColor` để đổi được trên nền ảnh hoặc nền trắng.
 */
export function VsfBrand({ href = "/", size = 26 }: { href?: string; size?: number }) {
  const t = useTranslations("landing.nav");

  return (
    <Link
      href={href}
      aria-label={t("brand")}
      style={{ display: "inline-flex", alignItems: "center", gap: 10, color: "inherit" }}
    >
      <svg aria-hidden="true" width={size} height={size} viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="9" fill="currentColor" opacity="0.16" />
        <path
          d="M8 10.5A3.5 3.5 0 0 1 11.5 7h9A3.5 3.5 0 0 1 24 10.5v6a3.5 3.5 0 0 1-3.5 3.5H15l-4.2 3.6c-.6.5-1.5.1-1.5-.7V20A3.5 3.5 0 0 1 8 16.5v-6Z"
          fill="currentColor"
        />
        <path d="M12.5 13.5h7M12.5 16.5h4.5" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" opacity="0.9" />
      </svg>
      <span style={{ fontSize: Math.round(size * 0.66), fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1 }}>
        {t("brand")}
      </span>
    </Link>
  );
}
