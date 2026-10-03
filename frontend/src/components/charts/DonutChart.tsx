"use client";

import { useState } from "react";

import { slotColor, type ChartSlot } from "./chartTheme";
import styles from "./Charts.module.scss";

export type DonutSlice = { key: string; label: string; value: number; slot: ChartSlot };

const SIZE = 156;
const STROKE = 18;
const GAP_PX = 2;

/**
 * Biểu đồ tròn (vòng khuyết) cho cơ cấu: mỗi cung cách nhau 2px, tổng ở giữa; trỏ chuột/lấy tiêu điểm vào cung hoặc dòng
 * chú thích thì giữa vòng đổi sang số và tỷ lệ của phần đó. Phần bằng 0 không vẽ nhưng vẫn có dòng chú thích (có số).
 */
export function DonutChart({
  slices,
  centerValue,
  centerLabel,
  ariaLabel,
  formatValue = String,
}: {
  slices: DonutSlice[];
  centerValue: string;
  centerLabel: string;
  ariaLabel: string;
  formatValue?: (value: number) => string;
}) {
  const [active, setActive] = useState<string | null>(null);

  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  const radius = (SIZE - STROKE) / 2;
  const circumference = 2 * Math.PI * radius;
  const shown = slices.filter((slice) => slice.value > 0);
  const gap = shown.length > 1 ? GAP_PX : 0;
  const current = slices.find((slice) => slice.key === active);

  let offset = 0;

  return (
    <div className={styles.donut}>
      <div className={styles.donutChart} style={{ width: SIZE, height: SIZE }}>
        <svg aria-label={ariaLabel} height={SIZE} role="img" viewBox={`0 0 ${SIZE} ${SIZE}`} width={SIZE}>
          <circle className={styles.donutTrack} cx={SIZE / 2} cy={SIZE / 2} fill="none" r={radius} strokeWidth={STROKE} />
          {total > 0
            ? shown.map((slice) => {
                const length = (slice.value / total) * circumference;
                const rotation = (offset / circumference) * 360 - 90;
                offset += length;
                return (
                  <circle
                    className={styles.donutSlice}
                    cx={SIZE / 2}
                    cy={SIZE / 2}
                    fill="none"
                    key={slice.key}
                    onPointerEnter={() => setActive(slice.key)}
                    onPointerLeave={() => setActive(null)}
                    opacity={active === null || active === slice.key ? 1 : 0.35}
                    r={radius}
                    stroke={slotColor(slice.slot)}
                    strokeDasharray={`${Math.max(0.5, length - gap)} ${circumference - Math.max(0.5, length - gap)}`}
                    strokeWidth={STROKE}
                    transform={`rotate(${rotation} ${SIZE / 2} ${SIZE / 2})`}
                  />
                );
              })
            : null}
        </svg>
        <div className={styles.donutCenter}>
          {current ? (
            <>
              <b>{formatValue(current.value)}</b>
              <small>{`${current.label} · ${total > 0 ? Math.round((100 * current.value) / total) : 0}%`}</small>
            </>
          ) : (
            <>
              <b>{centerValue}</b>
              <small>{centerLabel}</small>
            </>
          )}
        </div>
      </div>

      <ul className={styles.donutLegend}>
        {slices.map((slice) => (
          <li
            className={active === slice.key ? styles.legendActive : undefined}
            key={slice.key}
            onBlur={() => setActive(null)}
            onFocus={() => setActive(slice.key)}
            onPointerEnter={() => setActive(slice.key)}
            onPointerLeave={() => setActive(null)}
            tabIndex={0}
          >
            <i style={{ background: slotColor(slice.slot) }} />
            <span>{slice.label}</span>
            <b>{formatValue(slice.value)}</b>
            <em>{total > 0 ? `${Math.round((100 * slice.value) / total)}%` : "0%"}</em>
          </li>
        ))}
      </ul>
    </div>
  );
}
