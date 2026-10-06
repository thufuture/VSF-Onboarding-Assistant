import { slotColor, type TooltipRow } from "./chartTheme";
import styles from "./Charts.module.scss";

/** Chú giải nổi khi trỏ chuột/di phím vào một điểm: tiêu đề + từng dòng (ô màu, nhãn, giá trị). */
export function ChartTooltip({
  title,
  rows,
  left,
  top,
  side,
}: {
  title: string;
  rows: TooltipRow[];
  left: number;
  top: number;
  side: "left" | "right";
}) {
  return (
    <div
      className={`${styles.tooltip} ${side === "left" ? styles.tooltipLeft : styles.tooltipRight}`}
      role="status"
      style={{ left, top }}
    >
      <b>{title}</b>
      {rows.map((row) => (
        <div className={styles.tooltipRow} key={row.label}>
          {row.slot !== undefined ? <i style={{ background: slotColor(row.slot) }} /> : <i className={styles.noSwatch} />}
          <span>{row.label}</span>
          <strong>{row.value}</strong>
        </div>
      ))}
    </div>
  );
}

/** Chú thích màu (luôn có khi từ 2 chuỗi trở lên) để không phải dựa vào màu mới phân biệt được. */
export function ChartLegend({ items }: { items: { key: string; label: string; slot: TooltipRow["slot"]; value?: string }[] }) {
  return (
    <ul className={styles.legend}>
      {items.map((item) => (
        <li key={item.key}>
          <i style={{ background: slotColor(item.slot ?? "muted") }} />
          <span>{item.label}</span>
          {item.value !== undefined ? <b>{item.value}</b> : null}
        </li>
      ))}
    </ul>
  );
}
