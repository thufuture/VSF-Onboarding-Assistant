"use client";

import { useState, type KeyboardEvent, type PointerEvent } from "react";

import { ChartLegend, ChartTooltip } from "./ChartTooltip";
import { niceTicks, slotColor, useElementWidth, type ChartSeries } from "./chartTheme";
import styles from "./Charts.module.scss";

const PAD_TOP = 10;
const PAD_BOTTOM = 24;
const PAD_RIGHT = 14;

/**
 * Biểu đồ đường theo ngày: một trục y, đường 2px, lưới mờ, di chuột/phím mũi tên hiện đường dọc và chú giải.
 * Một chuỗi thì tô nhẹ phía dưới; từ hai chuỗi có chú thích màu. Vẽ bằng SVG thuần, không thư viện.
 */
export function LineChart({
  labels,
  titles,
  series,
  ariaLabel,
  formatValue = String,
  formatAxis,
  integer = false,
  height = 210,
}: {
  labels: string[];
  /** Tiêu đề đầy đủ của chú giải (mặc định dùng nhãn trục x). */
  titles?: string[];
  series: ChartSeries[];
  ariaLabel: string;
  formatValue?: (value: number) => string;
  formatAxis?: (value: number) => string;
  integer?: boolean;
  height?: number;
}) {
  const [wrapRef, width] = useElementWidth();
  const [active, setActive] = useState<number | null>(null);

  const count = labels.length;
  const ticks = niceTicks(Math.max(0, ...series.flatMap((s) => s.values)), integer);
  const top = ticks[ticks.length - 1] ?? 1;
  const axisLabels = ticks.map(formatAxis ?? formatValue);
  const left = 12 + Math.max(...axisLabels.map((label) => label.length)) * 6.4;
  const plotW = Math.max(60, width - left - PAD_RIGHT);
  const plotH = height - PAD_TOP - PAD_BOTTOM;

  const x = (index: number) => left + (count <= 1 ? plotW / 2 : (plotW * index) / (count - 1));
  const y = (value: number) => PAD_TOP + plotH - (value / top) * plotH;
  const labelStep = Math.max(1, Math.ceil(count / Math.max(2, Math.floor(plotW / 58))));

  const indexAt = (clientX: number, element: HTMLElement): number => {
    const offset = clientX - element.getBoundingClientRect().left - left;
    return Math.min(count - 1, Math.max(0, Math.round(count <= 1 ? 0 : (offset / plotW) * (count - 1))));
  };
  const onMove = (event: PointerEvent<HTMLDivElement>) => setActive(indexAt(event.clientX, event.currentTarget));
  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowLeft" ? -1 : 1;
    setActive((current) => Math.min(count - 1, Math.max(0, (current ?? (delta < 0 ? count : -1)) + delta)));
  };

  const single = series.length === 1;

  return (
    <div className={styles.chartBody}>
      <div
        aria-label={ariaLabel}
        className={styles.plot}
        onBlur={() => setActive(null)}
        onKeyDown={onKey}
        onPointerLeave={() => setActive(null)}
        onPointerMove={onMove}
        ref={wrapRef}
        role="group"
        tabIndex={0}
      >
        <svg aria-hidden="true" height={height} width={width}>
          {ticks.map((tick, index) => (
            <g key={tick}>
              <line className={index === 0 ? styles.axis : styles.grid} x1={left} x2={left + plotW} y1={y(tick)} y2={y(tick)} />
              <text className={styles.tickText} textAnchor="end" x={left - 8} y={y(tick) + 4}>
                {axisLabels[index]}
              </text>
            </g>
          ))}
          {labels.map((label, index) =>
            index % labelStep === 0 ? (
              <text className={styles.tickText} key={`${label}-${index}`} textAnchor="middle" x={x(index)} y={height - 7}>
                {label}
              </text>
            ) : null,
          )}
          {active !== null ? (
            <line className={styles.cursor} x1={x(active)} x2={x(active)} y1={PAD_TOP} y2={PAD_TOP + plotH} />
          ) : null}
          {series.map((item) => {
            const points = item.values.map((value, index) => `${x(index)},${y(value)}`).join(" ");
            const color = slotColor(item.slot);
            return (
              <g key={item.key}>
                {single && count > 1 ? (
                  <polygon fill={color} opacity={0.1} points={`${x(0)},${y(0)} ${points} ${x(count - 1)},${y(0)}`} />
                ) : null}
                <polyline
                  fill="none"
                  points={points}
                  stroke={color}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                />
                {active === null
                  ? item.values.map((value, index) =>
                      count === 1 || index === count - 1 ? (
                        <circle className={styles.dotRing} cx={x(index)} cy={y(value)} fill={color} key={index} r={4} />
                      ) : null,
                    )
                  : null}
                {active !== null ? (
                  <circle
                    className={styles.dotRing}
                    cx={x(active)}
                    cy={y(item.values[active] ?? 0)}
                    fill={color}
                    r={4.5}
                  />
                ) : null}
              </g>
            );
          })}
        </svg>
        {active !== null ? (
          <ChartTooltip
            left={x(active)}
            rows={series.map((item) => ({
              label: item.label,
              slot: item.slot,
              value: formatValue(item.values[active] ?? 0),
            }))}
            side={x(active) > width / 2 ? "left" : "right"}
            title={titles?.[active] ?? labels[active] ?? ""}
            top={PAD_TOP + 4}
          />
        ) : null}
      </div>
      {single ? null : (
        <ChartLegend items={series.map((item) => ({ key: item.key, label: item.label, slot: item.slot }))} />
      )}
    </div>
  );
}
