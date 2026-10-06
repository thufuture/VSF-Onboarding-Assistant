"use client";

import { useState, type KeyboardEvent, type PointerEvent } from "react";

import { ChartLegend, ChartTooltip } from "./ChartTooltip";
import { niceTicks, slotColor, useElementWidth, type ChartSeries, type TooltipRow } from "./chartTheme";
import styles from "./Charts.module.scss";

const PAD_TOP = 10;
const PAD_BOTTOM = 26;
const PAD_RIGHT = 8;
const GAP = 2;

export type BarCategory = {
  key: string;
  label: string;
  /** Tiêu đề chú giải (mặc định là nhãn). */
  title?: string;
  /** Dòng thêm trong chú giải, ví dụ số tài liệu và token của một lượt chạy. */
  extra?: TooltipRow[];
};

/** Thanh có đầu trên bo tròn, đáy phẳng bám trục (đầu dữ liệu bo, gốc không bo). */
function topRounded(x: number, y: number, w: number, h: number, r: number): string {
  const rr = Math.min(r, w / 2, h);
  return `M${x},${y + h} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + w - rr} Q${x + w},${y} ${x + w},${y + rr} V${y + h} Z`;
}

/**
 * Biểu đồ cột đứng, xếp chồng (mỗi đoạn cách nhau 2px) hoặc đặt cạnh nhau. Di chuột/phím mũi tên vào một cột hiện chú giải
 * đủ các chuỗi và các dòng `extra` của cột đó. Một trục y duy nhất; hai đại lượng khác thang thì tách thành hai biểu đồ.
 */
export function BarChart({
  categories,
  series,
  ariaLabel,
  stacked = false,
  formatValue = String,
  formatAxis,
  integer = false,
  height = 220,
}: {
  categories: BarCategory[];
  series: ChartSeries[];
  ariaLabel: string;
  stacked?: boolean;
  formatValue?: (value: number) => string;
  formatAxis?: (value: number) => string;
  integer?: boolean;
  height?: number;
}) {
  const [wrapRef, width] = useElementWidth();
  const [active, setActive] = useState<number | null>(null);

  const count = categories.length;
  const peak = stacked
    ? Math.max(0, ...categories.map((_, index) => series.reduce((sum, item) => sum + (item.values[index] ?? 0), 0)))
    : Math.max(0, ...series.flatMap((item) => item.values));
  const ticks = niceTicks(peak, integer);
  const top = ticks[ticks.length - 1] ?? 1;
  const axisLabels = ticks.map(formatAxis ?? formatValue);
  const left = 12 + Math.max(...axisLabels.map((label) => label.length)) * 6.4;
  const plotW = Math.max(60, width - left - PAD_RIGHT);
  const plotH = height - PAD_TOP - PAD_BOTTOM;
  const band = plotW / Math.max(1, count);
  const base = PAD_TOP + plotH;
  const groupW = Math.min(band * 0.72, stacked ? 40 : 30 * series.length);
  const barW = stacked ? groupW : Math.max(4, (groupW - GAP * (series.length - 1)) / series.length);
  const y = (value: number) => base - (value / top) * plotH;
  // Nhãn dài ("Chưa phân nhóm", "25/09 10:10") cần chỗ rộng hơn: chỉ hiện mỗi N nhãn để không chồng lên nhau.
  const labelWidth = Math.max(52, Math.max(0, ...categories.map((category) => category.label.length)) * 6.2 + 10);
  const labelStep = Math.max(1, Math.ceil(labelWidth / band));

  const onMove = (event: PointerEvent<HTMLDivElement>) => {
    const offset = event.clientX - event.currentTarget.getBoundingClientRect().left - left;
    setActive(offset < 0 || offset > plotW ? null : Math.min(count - 1, Math.floor(offset / band)));
  };
  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowLeft" ? -1 : 1;
    setActive((current) => Math.min(count - 1, Math.max(0, (current ?? (delta < 0 ? count : -1)) + delta)));
  };

  const centerOf = (index: number) => left + band * index + band / 2;
  const activeCategory = active === null ? undefined : categories[active];

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
          {active !== null ? (
            <rect className={styles.hoverBand} height={plotH} width={band} x={left + band * active} y={PAD_TOP} />
          ) : null}
          {categories.map((category, index) => {
            const startX = centerOf(index) - groupW / 2;
            let stackedTop = base;
            const lastVisible = stacked ? series.map((item) => (item.values[index] ?? 0) > 0).lastIndexOf(true) : -1;
            return (
              <g key={category.key}>
                {series.map((item, seriesIndex) => {
                  const value = item.values[index] ?? 0;
                  if (value <= 0) return null;
                  const h = Math.max(1, (value / top) * plotH);
                  if (stacked) {
                    const segmentTop = stackedTop - h;
                    const drawH = Math.max(1, h - (stackedTop < base ? GAP : 0));
                    stackedTop = segmentTop;
                    return seriesIndex === lastVisible ? (
                      <path d={topRounded(startX, segmentTop, barW, drawH, 3)} fill={slotColor(item.slot)} key={item.key} />
                    ) : (
                      <rect fill={slotColor(item.slot)} height={drawH} key={item.key} width={barW} x={startX} y={segmentTop} />
                    );
                  }
                  return (
                    <path
                      d={topRounded(startX + seriesIndex * (barW + GAP), base - h, barW, h, 3)}
                      fill={slotColor(item.slot)}
                      key={item.key}
                    />
                  );
                })}
                {index % labelStep === 0 ? (
                  <text className={styles.tickText} textAnchor="middle" x={centerOf(index)} y={height - 8}>
                    {category.label}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
        {active !== null && activeCategory ? (
          <ChartTooltip
            left={centerOf(active)}
            rows={[
              ...series.map((item) => ({
                label: item.label,
                slot: item.slot,
                value: formatValue(item.values[active] ?? 0),
              })),
              ...(activeCategory.extra ?? []),
            ]}
            side={centerOf(active) > width / 2 ? "left" : "right"}
            title={activeCategory.title ?? activeCategory.label}
            top={PAD_TOP + 4}
          />
        ) : null}
      </div>
      {series.length > 1 ? (
        <ChartLegend items={series.map((item) => ({ key: item.key, label: item.label, slot: item.slot }))} />
      ) : null}
    </div>
  );
}
