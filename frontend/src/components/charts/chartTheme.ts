import { useEffect, useRef, useState } from "react";

/**
 * Màu biểu đồ theo thứ tự cố định (không xoay vòng): xanh dương, cam, xanh ngọc, vàng, hồng; "muted" cho nhóm
 * "không có / đang khóa". Giá trị thật nằm ở biến CSS `--chart-N` trong Charts.module.scss (sáng/tối riêng).
 */
export type ChartSlot = 1 | 2 | 3 | 4 | 5 | "muted";

export type ChartSeries = {
  key: string;
  label: string;
  slot: ChartSlot;
  /** Cùng độ dài với danh mục (trục x). */
  values: number[];
};

export type TooltipRow = { label: string; value: string; slot?: ChartSlot };

export function slotColor(slot: ChartSlot): string {
  return slot === "muted" ? "var(--chart-muted)" : `var(--chart-${slot})`;
}

/** Mốc trục y "tròn": 0, step, 2·step… đủ phủ `maxValue`; số đếm (integer) luôn là số nguyên. */
export function niceTicks(maxValue: number, integer: boolean): number[] {
  const safe = maxValue > 0 ? maxValue : 1;
  const raw = safe / 4;
  const power = 10 ** Math.floor(Math.log10(raw));
  const steps = integer ? [1, 2, 5, 10] : [1, 2, 2.5, 5, 10];
  let step = steps.map((s) => s * power).find((s) => s >= raw) ?? 10 * power;
  if (integer && step < 1) step = 1;
  const count = Math.max(1, Math.ceil(safe / step - 1e-9));
  return Array.from({ length: count + 1 }, (_, i) => Number((i * step).toPrecision(12)));
}

/** Đo bề rộng thật của khung để vẽ chữ đúng cỡ (SVG co giãn sẽ làm chữ nhỏ đi trên màn hẹp). */
export function useElementWidth(fallback = 640) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const node = ref.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const next = Math.round(entries[0]?.contentRect.width ?? 0);
      if (next > 0) setWidth(next);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}
