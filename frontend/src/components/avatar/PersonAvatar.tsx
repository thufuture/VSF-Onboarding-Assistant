// Cổng thẳng từ AVS/personSvg/avKey của prototype v15 (roadmap chia sẻ) — giữ đúng màu da/tóc/trang phục
// và cách chọn biến thể theo tên, chỉ đổi cách vẽ từ chuỗi HTML sang SVG React.
import styles from "./PersonAvatar.module.scss";

type AvatarVariant = {
  g: "m" | "f";
  skin: string;
  neck: string;
  hair: string;
  hs: "short" | "side" | "buzz" | "long" | "bob" | "pony" | "bun" | "pixie";
  suit: string;
  lap: string;
  acc: string;
  blouse?: string;
  glasses?: true;
  bg: string;
  bg2: string;
};

const AVS: Record<string, AvatarVariant> = {
  m1: { g: "m", skin: "#f4c8a4", neck: "#e9b28c", hair: "#2c2438", hs: "short", suit: "#0c2d5b", lap: "#123d78", acc: "#1090cb", bg: "#d3e9f7", bg2: "#e3f1fb" },
  f1: { g: "f", skin: "#f4c8a4", neck: "#e9b28c", hair: "#2c2438", hs: "long", suit: "#0c2d5b", lap: "#123d78", acc: "#c9a24a", blouse: "#ffffff", bg: "#dfe6f7", bg2: "#ecf0fb" },
  m2: { g: "m", skin: "#e3b08a", neck: "#d19a72", hair: "#3b2a20", hs: "side", suit: "#2f3a4a", lap: "#3b4759", acc: "#7a8aa0", glasses: true, bg: "#e2e8ee", bg2: "#eef2f6" },
  f2: { g: "f", skin: "#e3b08a", neck: "#d19a72", hair: "#4a3020", hs: "bob", suit: "#1f6f6a", lap: "#2a827c", acc: "#e9c46a", blouse: "#f6f1e7", bg: "#d6ece9", bg2: "#e6f4f2" },
  m3: { g: "m", skin: "#c68f68", neck: "#b27a54", hair: "#1e1b22", hs: "short", suit: "#1f4f5a", lap: "#28626f", acc: "#d9a441", bg: "#d7ebe8", bg2: "#e7f3f1" },
  f3: { g: "f", skin: "#f1c9a8", neck: "#e0b08a", hair: "#1e1b22", hs: "pony", suit: "#5b2b3a", lap: "#6d3547", acc: "#d8c3a5", blouse: "#ffffff", bg: "#efe1e6", bg2: "#f6ecef" },
  m4: { g: "m", skin: "#f1c9a8", neck: "#e0b08a", hair: "#6b4a2f", hs: "side", suit: "#3a3f6b", lap: "#474d7f", acc: "#b0476a", bg: "#e2e4f4", bg2: "#eeeffa" },
  f4: { g: "f", skin: "#dba57c", neck: "#c78f66", hair: "#3b2a20", hs: "bun", suit: "#2f3a4a", lap: "#3b4759", acc: "#8fa3ba", blouse: "#eaf1f8", glasses: true, bg: "#e3e8ee", bg2: "#eef1f5" },
  m5: { g: "m", skin: "#dba57c", neck: "#c78f66", hair: "#171618", hs: "buzz", suit: "#4a5568", lap: "#5a6579", acc: "#0e7fb3", bg: "#dde6ee", bg2: "#eaf0f5" },
  f5: { g: "f", skin: "#f6d2b4", neck: "#e8bc98", hair: "#7a4b2a", hs: "long", suit: "#3f4a8f", lap: "#4b57a3", acc: "#e9c46a", blouse: "#ffffff", bg: "#e2e5f6", bg2: "#eef0fb" },
  m6: { g: "m", skin: "#f6d2b4", neck: "#e8bc98", hair: "#8a6a3f", hs: "short", suit: "#1f3b57", lap: "#2a4c6d", acc: "#4f5bbf", bg: "#d9e6f2", bg2: "#e7f0f8" },
  f6: { g: "f", skin: "#c68f68", neck: "#b27a54", hair: "#2c2438", hs: "pixie", suit: "#3f5468", lap: "#4b6279", acc: "#f0c987", blouse: "#ffffff", bg: "#dde5ec", bg2: "#eaeff4" },
};

const AV_ORDER = ["m1", "f1", "m2", "f2", "m3", "f3", "m4", "f4", "m5", "f5", "m6", "f6"];

const FRONT_HAIR: Record<string, string> = {
  short: "M20.4 26.6c-1.9-11.6 6.4-17.2 13.4-16.6 8 .6 12.6 7 10.6 16.6-1.8-6.2-5.7-9.6-11.6-9.6-5.4 0-9.4 3-12.4 9.6z",
  side: "M20.6 26c-1.4-10.6 5.6-16.2 13-15.8 7.8.4 12 6.8 10.6 15.8-1.8-5.6-4.8-8.6-9.6-8.8-4.8.6-9.4 3-14 8.8z",
  buzz: "M21.2 25c-.8-8.6 5.2-13.4 10.8-13.4S43.6 16.4 42.8 25c-3.2-5-6.4-6.6-10.8-6.6S24.4 20 21.2 25z",
  long: "M20.8 27c-.6-9 4.6-14.4 11.4-14.4s12 5.4 11.4 14.4c-2.4-5-5.8-7.6-11.2-7.6s-8.6 2.6-11.6 7.6z",
  bob: "M21 26.5c.2-8.4 4.8-13.8 11.2-13.8 6.6 0 11.4 5.8 11 13.8-3.2-5.4-6.6-7.6-11-7.2-4.6 0-8 2.4-11.2 7.2z",
  pony: "M20.4 26.6c-1.9-11.6 6.4-17.2 13.4-16.6 8 .6 12.6 7 10.6 16.6-1.8-6.2-5.7-9.6-11.6-9.6-5.4 0-9.4 3-12.4 9.6z",
  bun: "M20.6 26c-1.4-10.6 5.6-16.2 13-15.8 7.8.4 12 6.8 10.6 15.8-1.8-5.6-4.8-8.6-9.6-8.8-4.8.6-9.4 3-14 8.8z",
  pixie: "M20.8 26c-1.6-10.4 5-16 12-15.8 7.6.2 11.8 6 11 15.8-.6-3.6-2-5.6-4.4-7-2.4 1.2-6.4 1.6-10 .4-3.4 1.2-6 3.4-8.6 6.6z",
};

const BACK_HAIR: Record<string, string> = {
  long: "M18.6 28c-1.6-12.6 5.2-19 13.4-19s15 6.4 13.4 19c.4 8-1 14.6-3.6 18.4H22.2c-2.6-3.8-4-10.4-3.6-18.4z",
  bob: "M18.8 30c-1.4-13 5-19.6 13.2-19.6S45.6 17 44.2 30c.2 4.4-1 7.4-3 9.2H21.8c-2-1.8-3.2-4.8-3-9.2z",
  pony: "M42 18c6.4 1 9.4 7.4 7.4 14.6-.8-4.4-3.4-6.6-6.8-7z",
};

/** Ký tự đầu (bỏ dấu) của họ trong tên tiếng Việt "Họ Đệm Tên" -> chọn 1 trong 12 biến thể (m1..f6). */
function avKey(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const surname = words[0] ?? "A";
  const normalized = surname
    .replace("Đ", "D")
    .replace("đ", "d")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toUpperCase();
  const index = Math.max(0, (normalized.charCodeAt(0) || 65) - 65);
  return AV_ORDER[index % 12] ?? "m1";
}

export function PersonAvatar({ name, sizePx = 32 }: { name: string; sizePx?: number }) {
  const variant = AVS[avKey(name)] ?? AVS.m1;
  const isFemale = variant.g === "f";
  const back = BACK_HAIR[variant.hs];
  const front = FRONT_HAIR[variant.hs];

  return (
    <span className={styles.pav} style={{ width: sizePx, height: sizePx }} title={name}>
      <svg height={sizePx} role="img" viewBox="0 0 64 64" width={sizePx} aria-label="Avatar">
        <circle cx="32" cy="32" fill={variant.bg} r="32" />
        <circle cx="32" cy="34" fill={variant.bg2} r="26" />
        {back ? <path d={back} fill={variant.hair} /> : null}
        {variant.hs === "bun" ? <circle cx="32" cy="10.6" fill={variant.hair} r="4.9" /> : null}
        <path d="M6.5 62c1.4-11.5 10-17.5 25.5-17.5S56.1 50.5 57.5 62z" fill={variant.suit} />
        {isFemale ? (
          <>
            <path d="M25 44.6 32 55.6 39 44.6z" fill={variant.blouse} />
            <path d="M22 46.4 32 58.4 26.6 45.4z" fill={variant.lap} />
            <path d="M42 46.4 32 58.4 37.4 45.4z" fill={variant.lap} />
            <circle cx="32" cy="55.6" fill={variant.acc} r="1.1" />
          </>
        ) : (
          <>
            <path d="M24.5 45.5 32 56l7.5-10.5-3.2-3H27.7z" fill="#ffffff" />
            <path d="M30.6 47.5h2.8l1.6 9.2L32 60l-3-3.3z" fill={variant.acc} />
            <path d="M22 46.5 32 58.5 26 46z" fill={variant.lap} />
            <path d="M42 46.5 32 58.5 38 46z" fill={variant.lap} />
          </>
        )}
        <rect fill={variant.neck} height="9" rx="3.4" width="8.8" x="27.6" y="35.5" />
        <ellipse cx="32" cy="26.5" fill={variant.skin} rx="11.2" ry="12.6" />
        <path d={front} fill={variant.hair} />
        <ellipse cx="27.6" cy="27.8" fill="#1b1a2b" rx="1.5" ry="1.8" />
        <ellipse cx="36.4" cy="27.8" fill="#1b1a2b" rx="1.5" ry="1.8" />
        <circle cx="28.1" cy="27.1" fill="#fff" r=".55" />
        <circle cx="36.9" cy="27.1" fill="#fff" r=".55" />
        <path
          d="M24.8 24.2c1.4-1 3-1.2 4.4-.6M34.8 23.6c1.4-.6 3-.4 4.4.6"
          fill="none"
          stroke={variant.hair}
          strokeLinecap="round"
          strokeWidth="1.1"
        />
        <path
          d="M28.4 33.2c1.7 2 5.5 2 7.2 0"
          fill="none"
          stroke="#a4523b"
          strokeLinecap="round"
          strokeWidth="1.5"
        />
        <circle cx="24.6" cy="31.4" fill="#ee9a8a" opacity="0.42" r="1.9" />
        <circle cx="39.4" cy="31.4" fill="#ee9a8a" opacity="0.42" r="1.9" />
        {variant.glasses ? (
          <g fill="none" stroke="#1b1a2b" strokeWidth="1.1">
            <circle cx="27.6" cy="27.8" r="3.7" />
            <circle cx="36.4" cy="27.8" r="3.7" />
            <path d="M31.3 27.6h1.4" />
          </g>
        ) : null}
      </svg>
    </span>
  );
}
