import type { ReactNode } from "react";

export type FlatIconName =
  | "dashboard"
  | "users"
  | "user"
  | "flag"
  | "mail"
  | "tasks"
  | "book"
  | "sparkle"
  | "link"
  | "building"
  | "network"
  | "route"
  | "clock"
  | "laptop"
  | "file"
  | "award"
  | "chat"
  | "lifebuoy";

export type FlatTone = "blue" | "teal" | "indigo" | "amber" | "rose" | "slate" | "green";

// Mỗi tông gồm màu chính và màu nhạt đi kèm — icon phẳng hai màu (kiểu Flaticon "flat/duotone"), không viền mảnh.
const TONES: Record<FlatTone, [string, string]> = {
  blue: ["#1b6fb8", "#a9cdec"],
  teal: ["#1a8a84", "#a6d9d5"],
  indigo: ["#4457b3", "#bcc4ee"],
  amber: ["#d18a12", "#f5d79a"],
  rose: ["#c0455e", "#eeb8c4"],
  slate: ["#5b6c81", "#c3ccd8"],
  green: ["#1f8a5f", "#a6dcc3"],
};

// Hình vẽ trên lưới 32×32; `a` = màu chính, `b` = màu nhạt. Muốn dùng icon Flaticon thật, thay thân hàm tương ứng bằng SVG tải về.
const SHAPES: Record<FlatIconName, (a: string, b: string) => ReactNode> = {
  dashboard: (a, b) => (
    <>
      <rect fill={a} height="10" rx="3" width="10" x="4" y="4" />
      <rect fill={b} height="10" rx="3" width="10" x="18" y="4" />
      <rect fill={b} height="10" rx="3" width="10" x="4" y="18" />
      <rect fill={a} height="10" rx="3" width="10" x="18" y="18" />
    </>
  ),
  users: (a, b) => (
    <>
      <path d="M18 27c0-4.4 2.7-7.5 6.2-7.5S30 22.600 30 27z" fill={b} />
      <circle cx="24" cy="12" fill={b} r="4.200" />
      <path d="M2 27c0-6 4.400-10 10-10s10 4 10 10z" fill={a} />
      <circle cx="12" cy="10.500" fill={a} r="5.500" />
    </>
  ),
  user: (a, b) => (
    <>
      <path d="M5 28c0-6.200 5-10 11-10s11 3.800 11 10z" fill={b} />
      <circle cx="16" cy="11" fill={a} r="6.500" />
    </>
  ),
  flag: (a, b) => (
    <>
      <rect fill={b} height="25" rx="1.500" width="3" x="6" y="4" />
      <path d="M9 6h17l-4.500 5.500L26 17H9z" fill={a} />
    </>
  ),
  mail: (a, b) => (
    <>
      <rect fill={b} height="19" rx="4" width="27" x="2.500" y="6.500" />
      <path d="M4.500 10.500 16 19.500l11.500-9" fill="none" stroke={a} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.800" />
    </>
  ),
  tasks: (a, b) => (
    <>
      <rect fill={b} height="24" rx="4" width="21" x="5.500" y="5" />
      <rect fill={a} height="7" rx="3" width="11" x="10.500" y="2.500" />
      <path d="m10.500 15.500 2 2 3.500-4" fill="none" stroke={a} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.400" />
      <rect fill={a} height="2.400" rx="1.200" width="5" x="18" y="15" />
      <path d="m10.500 22.500 2 2 3.500-4" fill="none" stroke={a} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.400" />
      <rect fill={a} height="2.400" rx="1.200" width="5" x="18" y="22" />
    </>
  ),
  book: (a, b) => (
    <>
      <path d="M16 8.500C12.500 5.500 7.500 5 3 6v19c4.500-1 9.500-.5 13 2.500z" fill={a} />
      <path d="M16 8.500c3.500-3 8.500-3.500 13-2.500v19c-4.500-1-9.500-.5-13 2.500z" fill={b} />
    </>
  ),
  sparkle: (a, b) => (
    <>
      <path d="M13.500 4 16 11.500 23.500 14 16 16.500 13.500 24 11 16.500 3.500 14 11 11.500z" fill={a} />
      <path d="m25 3.500 1.200 3.300 3.300 1.200-3.300 1.200L25 12.500l-1.200-3.300L20.500 8l3.300-1.200z" fill={b} />
      <path d="m24 19.500 1 2.700 2.700 1-2.700 1-1 2.700-1-2.700-2.700-1 2.700-1z" fill={b} />
    </>
  ),
  link: (a, b) => (
    <>
      <rect fill="none" height="9" rx="4.500" stroke={a} strokeWidth="3.200" width="15" x="2.500" y="7" />
      <rect fill="none" height="9" rx="4.500" stroke={b} strokeWidth="3.200" width="15" x="14.500" y="16" />
      <path d="m12 18 8-4" fill="none" stroke={a} strokeLinecap="round" strokeWidth="3.200" />
    </>
  ),
  building: (a, b) => (
    <>
      <rect fill={a} height="25" rx="2.500" width="15" x="5" y="4" />
      <rect fill={b} height="16" rx="2.500" width="8" x="19" y="13" />
      <g fill={b}>
        <rect height="3" rx=".8" width="3" x="8.500" y="8" />
        <rect height="3" rx=".8" width="3" x="13.500" y="8" />
        <rect height="3" rx=".8" width="3" x="8.500" y="14" />
        <rect height="3" rx=".8" width="3" x="13.500" y="14" />
        <rect height="4" rx=".8" width="4" x="10.500" y="22" />
      </g>
      <g fill={a}>
        <rect height="2.400" rx=".8" width="2.400" x="21.800" y="16" />
        <rect height="2.400" rx=".8" width="2.400" x="21.800" y="21" />
      </g>
    </>
  ),
  network: (a, b) => (
    <>
      <path d="M16 11 9 20M16 11l7 9M11 24h10" fill="none" stroke={b} strokeLinecap="round" strokeWidth="2.600" />
      <circle cx="16" cy="8" fill={a} r="4.800" />
      <circle cx="8" cy="24" fill={b} r="4.800" />
      <circle cx="24" cy="24" fill={b} r="4.800" />
    </>
  ),
  route: (a, b) => (
    <>
      <path d="M8 24C8 14 24 21 24 9" fill="none" stroke={b} strokeDasharray="1 5.200" strokeLinecap="round" strokeWidth="3.400" />
      <circle cx="8" cy="24" fill={a} r="4.500" />
      <circle cx="24" cy="8" fill={a} r="4.500" />
      <circle cx="8" cy="24" fill="#fff" r="1.700" />
      <circle cx="24" cy="8" fill="#fff" r="1.700" />
    </>
  ),
  clock: (a, b) => (
    <>
      <circle cx="16" cy="16" fill={b} r="12.500" />
      <path d="M16 8.500V16l5 3.200" fill="none" stroke={a} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.800" />
    </>
  ),
  laptop: (a, b) => (
    <>
      <rect fill={a} height="15" rx="2.800" width="21" x="5.500" y="6" />
      <rect fill={b} height="10" rx="1.200" width="16" x="8" y="8.500" />
      <path d="M2.500 24h27l-1.800 3.200H4.300z" fill={a} />
    </>
  ),
  file: (a, b) => (
    <>
      <path d="M8 3h11l8 8v16a2.400 2.400 0 0 1-2.400 2.400H8A2.400 2.400 0 0 1 5.600 27V5.400A2.400 2.400 0 0 1 8 3z" fill={a} />
      <path d="M19 3v6.200a1.800 1.800 0 0 0 1.800 1.800H27z" fill={b} />
      <rect fill={b} height="2.400" rx="1.200" width="12" x="10" y="16" />
      <rect fill={b} height="2.400" rx="1.200" width="8.500" x="10" y="21.500" />
    </>
  ),
  award: (a, b) => (
    <>
      <path d="m10.500 20-3 9 5-2.500 3.200 3 1.800-8.500z" fill={b} />
      <path d="m21.500 20 3 9-5-2.500-3.200 3-1.800-8.500z" fill={b} />
      <circle cx="16" cy="12.500" fill={a} r="9.500" />
      <circle cx="16" cy="12.500" fill={b} r="5.200" />
    </>
  ),
  chat: (a, b) => (
    <>
      <path d="M4 9a4.500 4.500 0 0 1 4.500-4.500h15A4.500 4.500 0 0 1 28 9v10a4.500 4.500 0 0 1-4.500 4.500H14L8 28.500v-5H8.500A4.500 4.500 0 0 1 4 19z" fill={a} />
      <circle cx="10.500" cy="14" fill={b} r="1.900" />
      <circle cx="16" cy="14" fill={b} r="1.900" />
      <circle cx="21.500" cy="14" fill={b} r="1.900" />
    </>
  ),
  lifebuoy: (a, b) => (
    <>
      <circle cx="16" cy="16" fill={a} r="13" />
      <circle cx="16" cy="16" fill="#fff" r="5.500" />
      <path d="m6.800 6.800 5.700 5.700m7 7 5.700 5.700m0-18.400-5.700 5.700m-7 7-5.700 5.700" fill="none" stroke={b} strokeWidth="4.600" />
      <circle cx="16" cy="16" fill="none" r="5.500" stroke={a} strokeWidth="1.400" />
    </>
  ),
};

/** Icon phẳng hai tông màu: tông chọn theo ý nghĩa của mục, kích thước mặc định 26px. */
export function FlatIcon({ name, tone = "blue", size = 26 }: { name: FlatIconName; tone?: FlatTone; size?: number }) {
  const [a, b] = TONES[tone];
  return (
    <svg aria-hidden="true" focusable="false" height={size} viewBox="0 0 32 32" width={size}>
      {SHAPES[name](a, b)}
    </svg>
  );
}
