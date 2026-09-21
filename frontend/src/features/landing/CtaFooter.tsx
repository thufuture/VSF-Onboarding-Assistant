import { ArrowRight, Mail } from "lucide-react";
import Image from "next/image";
import { useTranslations } from "next-intl";

import { VsfBrand } from "@/components/brand/VsfBrand";
import { Link } from "@/i18n/navigation";

import styles from "./CtaFooter.module.scss";

const COMMONS = "https://commons.wikimedia.org/wiki/File:";

// Ảnh dùng trên landing (hero, khối vai trò, kêu gọi/chân trang). CC BY và CC BY-SA đều yêu cầu ghi tác giả và giấy phép;
// chi tiết từng tệp ở public/images/landing/CREDITS.md.
const PHOTO_CREDITS = [
  {
    author: "Steffen Schmitz",
    file: `${COMMONS}Ho_Chi_Minh_City,_Vincom_Center,_2020-01_CN-01.jpg`,
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/",
  },
  {
    author: "trungydang",
    file: `${COMMONS}Vincom_center,_Saigon_Vietnam_-_panoramio.jpg`,
    license: "CC BY 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by/3.0/",
  },
  {
    author: "pqthong0911",
    file: `${COMMONS}VINCOM_CENTER-HCM-VN_-_panoramio_(1).jpg`,
    license: "CC BY 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by/3.0/",
  },
] as const;

/** Phần kêu gọi cuối trang: ảnh nền tối, logo, tiêu đề và nút đăng nhập (giống bố cục phần kết của VLearn). */
export function CtaSection() {
  const t = useTranslations("landing.cta");

  return (
    <section className={styles.cta}>
      <Image alt="" className={styles.ctaPhoto} fill sizes="100vw" src="/images/landing/cta-vincom-towers.webp" />
      <div aria-hidden="true" className={styles.ctaShade} />
      <div className={styles.ctaInner}>
        <span className={styles.ctaLogo}>
          <VsfBrand size={40} />
        </span>
        <h2>{t("heading")}</h2>
        <p>{t("text")}</p>
        <Link className={styles.ctaButton} href="/login">
          {t("button")} <ArrowRight size={16} />
        </Link>
      </div>
    </section>
  );
}

/** Chân trang xanh có hình đường chân trời mờ ở bên phải, bốn cột và dòng ghi công ảnh. */
export function SiteFooter() {
  const t = useTranslations("landing.footer");
  const nav = useTranslations("landing.nav");

  return (
    <footer className={styles.footer}>
      <Image alt="" className={styles.footerPhoto} fill sizes="60vw" src="/images/landing/cta-vincom-towers.webp" />
      <div aria-hidden="true" className={styles.footerShade} />

      <div className={styles.footerInner}>
        <div className={styles.footerBrand}>
          <VsfBrand size={30} />
          <p>{t("tagline")}</p>
        </div>

        <div className={styles.footerCol}>
          <strong>{t("aboutTitle")}</strong>
          <a href="#how">{t("how")}</a>
          <a href="#roles">{t("roles")}</a>
        </div>

        <div className={styles.footerCol}>
          <strong>{t("accessTitle")}</strong>
          <Link href="/login">{t("login")}</Link>
          <a href="#hero">{nav("top")}</a>
        </div>

        <div className={styles.footerCol}>
          <strong>{t("contactTitle")}</strong>
          <a className={styles.mail} href={`mailto:${t("email")}`}>
            <Mail size={14} />
            {t("email")}
          </a>
          <span>{t("contactLine")}</span>
          <span className={styles.note}>{t("contactNote")}</span>
        </div>
      </div>

      <div className={styles.footerBottom}>
        <span>{t("copyright")}</span>
        <span className={styles.credit}>
          {t("photoLead")}
          {PHOTO_CREDITS.map((photo, index) => (
            <span key={photo.author}>
              {index > 0 ? "; " : ""}
              <a href={photo.file} rel="noopener noreferrer" target="_blank">
                {photo.author}
              </a>{" "}
              (
              <a href={photo.licenseUrl} rel="noopener noreferrer" target="_blank">
                {photo.license}
              </a>
              )
            </span>
          ))}
          , {t("photoSource")} ({t("photoEdited")})
        </span>
      </div>
    </footer>
  );
}
