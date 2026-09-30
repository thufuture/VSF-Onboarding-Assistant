import Image from "next/image";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import type { ReactNode } from "react";

import styles from "./PageHero.module.scss";

// Ảnh minh họa trang trí (Vincom Center Đồng Khởi và khu trung tâm), ghi công ở chân trang và public/images/landing/CREDITS.md.
const SLIDES = [
  "/images/landing/hero-vincom-dong-khoi.webp",
  "/images/landing/roles-vincom-facade.webp",
  "/images/landing/cta-vincom-towers.webp",
];

/**
 * Dải ảnh đầu mỗi trang của nhân viên: ba ảnh tòa nhà trôi chậm qua lại, phủ xanh đậm, sóng nước chạy ở đáy để nối
 * mượt sang nền trang. Nội dung bên phải (vòng tiến độ, nút...) truyền qua `aside`.
 */
export function PageHero({
  title,
  subtitle,
  aside,
  avatarName,
  compact = false,
}: {
  title: string;
  subtitle?: string;
  aside?: ReactNode;
  /** Có tên thì banner hiện ảnh đại diện của người đang đăng nhập bên trái. */
  avatarName?: string;
  compact?: boolean;
}) {
  return (
    <section className={`${styles.hero} ${compact ? styles.compact : ""}`}>
      <div aria-hidden="true" className={styles.slides}>
        {SLIDES.map((src, index) => (
          <div className={styles.slide} key={src} style={{ animationDelay: `${index * 9}s` }}>
            <Image alt="" className={styles.photo} fill priority={index === 0} sizes="100vw" src={src} />
          </div>
        ))}
        <div className={styles.tint} />
      </div>

      <div className={styles.inner}>
        <div className={styles.text}>
          {avatarName ? (
            <span className={styles.avatar}>
              <PersonAvatar name={avatarName} sizePx={compact ? 52 : 62} />
            </span>
          ) : null}
          <div className={styles.textBody}>
            <h1>{title}</h1>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
        </div>
        {aside ? <div className={styles.aside}>{aside}</div> : null}
      </div>

      <div aria-hidden="true" className={styles.waves}>
        <svg className={styles.waveBack} preserveAspectRatio="none" viewBox="0 0 2880 90">
          <path d="M0 45 Q180 5 360 45 T720 45 T1080 45 T1440 45 T1800 45 T2160 45 T2520 45 T2880 45 V90 H0 Z" />
        </svg>
        <svg className={styles.waveFront} preserveAspectRatio="none" viewBox="0 0 2880 90">
          <path d="M0 55 Q240 15 480 55 T960 55 T1440 55 T1920 55 T2400 55 T2880 55 V90 H0 Z" />
        </svg>
      </div>
    </section>
  );
}
