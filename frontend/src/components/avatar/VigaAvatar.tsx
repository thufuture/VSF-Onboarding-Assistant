import styles from "./PersonAvatar.module.scss";

/**
 * Avatar của Viga — nhân viên hỗ trợ đeo tai nghe, cổng thẳng từ `vigaAvatar()` của prototype v15 (giữ nguyên
 * màu da, tóc, đồng phục và bộ tai nghe), chỉ đổi cách vẽ từ chuỗi HTML sang SVG React.
 */
export function VigaAvatar({ sizePx = 32 }: { sizePx?: number }) {
  return (
    <span className={styles.pav} style={{ width: sizePx, height: sizePx }}>
      <svg aria-label="Viga" height={sizePx} role="img" viewBox="0 0 64 64" width={sizePx}>
        <circle cx="32" cy="32" fill="#d3e9f7" r="32" />
        <circle cx="32" cy="34" fill="#e3f1fb" r="26" />
        <path d="M6.5 62c1.4-11.5 10-17.5 25.5-17.5S56.1 50.5 57.5 62z" fill="#0c2d5b" />
        <path d="M24.5 45.5 32 56l7.5-10.5-3.2-3H27.7z" fill="#ffffff" />
        <path d="M30.6 47.5h2.8l1.6 9.2L32 60l-3-3.3z" fill="#1090cb" />
        <path d="M22 46.5 32 58.5 26 46z" fill="#123d78" />
        <path d="M42 46.5 32 58.5 38 46z" fill="#123d78" />
        <rect fill="#e9b28c" height="9" rx="3.4" width="8.8" x="27.6" y="35.5" />
        <ellipse cx="32" cy="26.5" fill="#f4c8a4" rx="11.2" ry="12.6" />
        <path
          d="M20.4 26.6c-1.9-11.6 6.4-17.2 13.4-16.6 8 .6 12.6 7 10.6 16.6-1.8-6.2-5.7-9.6-11.6-9.6-5.4 0-9.4 3-12.4 9.6z"
          fill="#2c2438"
        />
        <path d="M20.6 26c.2-4.5 2.4-8 6-9.6-2.6 2.6-3.4 5.6-3.2 9.6z" fill="#3d3350" />
        <ellipse cx="27.6" cy="27.8" fill="#1b1a2b" rx="1.5" ry="1.8" />
        <ellipse cx="36.4" cy="27.8" fill="#1b1a2b" rx="1.5" ry="1.8" />
        <circle cx="28.1" cy="27.1" fill="#fff" r=".55" />
        <circle cx="36.9" cy="27.1" fill="#fff" r=".55" />
        <path
          d="M24.8 24.2c1.4-1 3-1.2 4.4-.6M34.8 23.6c1.4-.6 3-.4 4.4.6"
          fill="none"
          stroke="#2c2438"
          strokeLinecap="round"
          strokeWidth="1.1"
        />
        <path d="M28.4 33.2c1.7 2 5.5 2 7.2 0" fill="none" stroke="#a4523b" strokeLinecap="round" strokeWidth="1.5" />
        <circle cx="24.6" cy="31.4" fill="#ee9a8a" opacity=".45" r="1.9" />
        <circle cx="39.4" cy="31.4" fill="#ee9a8a" opacity=".45" r="1.9" />
        <path d="M20.4 27a11.6 11.6 0 0 1 23.2 0" fill="none" stroke="#1090cb" strokeLinecap="round" strokeWidth="2.3" />
        <rect fill="#1090cb" height="8.4" rx="2.3" width="4.6" x="17.8" y="25.6" />
        <rect fill="#1090cb" height="8.4" rx="2.3" width="4.6" x="41.6" y="25.6" />
        <path d="M42.6 33.6c0 4.4-3.4 6.4-8.4 6.4" fill="none" stroke="#1090cb" strokeLinecap="round" strokeWidth="1.7" />
        <circle cx="33.4" cy="40" fill="#0c2d5b" r="1.8" />
      </svg>
    </span>
  );
}
