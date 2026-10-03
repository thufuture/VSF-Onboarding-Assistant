import type { ChartSlot } from "@/components/charts/chartTheme";

/** Chi phí USD: số nhỏ giữ nhiều chữ số để thấy được (một lượt tạo task chỉ vài phần trăm xu). */
export function formatUsd(value: number): string {
  if (value === 0) return "0";
  if (value < 0.01) return value.toFixed(4);
  return value < 1 ? value.toFixed(3) : value.toFixed(2);
}

/** Nhãn trục chi phí: cùng số chữ số thập phân cho mọi mốc, bỏ số 0 thừa ("0.005", "0.01", "0.015"). */
export function formatUsdAxis(value: number): string {
  return value === 0 ? "0" : String(Number(value.toFixed(4)));
}

export function formatMs(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${Math.round(value)} ms`;
}

export function formatSeconds(value: number): string {
  if (value >= 100) return `${Math.round(value)} s`;
  return `${value.toFixed(value < 10 ? 2 : 1)} s`;
}

export function formatCount(value: number): string {
  return value.toLocaleString("vi-VN");
}

/** "2026-10-01" → "01/10" (nhãn trục x). */
export function dayLabel(iso: string): string {
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
}

/** "2026-10-01" → "Thứ Năm, 01/10/2026" theo ngôn ngữ giao diện (tiêu đề chú giải). */
export function dayTitle(iso: string, locale: string): string {
  const [year = 1970, month = 1, day = 1] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

/** Thời điểm bắt đầu một lượt chạy: "01/10 20:15" theo giờ máy người xem. */
export function runLabel(iso: string | null): string {
  if (iso === null) return "—";
  const date = new Date(iso);
  const two = (n: number) => String(n).padStart(2, "0");
  return `${two(date.getDate())}/${two(date.getMonth() + 1)} ${two(date.getHours())}:${two(date.getMinutes())}`;
}

/** Màu cố định theo thực thể để cùng một khái niệm giữ nguyên màu qua mọi biểu đồ. */
export const PROGRESS_SLOT: Record<string, ChartSlot> = {
  NO_JOURNEY: "muted",
  NOT_STARTED: 2,
  IN_PROGRESS: 1,
  COMPLETED: 3,
};

/** Chi phí theo thao tác: bốn thao tác tốn tiền nhất có màu riêng, còn lại gộp "Khác". */
export const OPERATION_SLOT: Record<string, ChartSlot> = {
  "chat.answer": 1,
  "task.proposal": 2,
  "viga.route": 3,
  "chat.rewrite": 4,
};

export const KNOWN_OPERATIONS = new Set([
  "chat.rewrite",
  "chat.embed",
  "chat.answer",
  "viga.route",
  "ingest.embed",
  "ingest.reembed",
  "ingest.probe",
  "ingest.structure",
  "task.proposal",
  "job",
]);
