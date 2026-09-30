import styles from "./DonutChart.module.scss";

export type DonutSlice = { key: string; label: string; value: number; color: string };

/**
 * Biểu đồ tròn (vòng khuyết) cho tiến độ: mỗi phần là một cung, tổng ở giữa. Vẽ bằng SVG thuần, không thư viện.
 * Phần bằng 0 được bỏ qua để không tạo vạch thừa.
 */
export function DonutChart({
  slices,
  centerValue,
  centerLabel,
  size = 148,
}: {
  slices: DonutSlice[];
  centerValue: string;
  centerLabel: string;
  size?: number;
}) {
  const shown = slices.filter((slice) => slice.value > 0);
  const total = shown.reduce((sum, slice) => sum + slice.value, 0);
  const stroke = 16;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;

  return (
    <div className={styles.wrap}>
      <div className={styles.chart} style={{ width: size, height: size }}>
        <svg height={size} role="img" viewBox={`0 0 ${size} ${size}`} width={size}>
          <circle
            className={styles.track}
            cx={size / 2}
            cy={size / 2}
            fill="none"
            r={radius}
            strokeWidth={stroke}
          />
          {total > 0
            ? shown.map((slice) => {
                const length = (slice.value / total) * circumference;
                const dash = `${length} ${circumference - length}`;
                const rotation = (offset / circumference) * 360 - 90;
                offset += length;
                return (
                  <circle
                    className={styles.slice}
                    cx={size / 2}
                    cy={size / 2}
                    fill="none"
                    key={slice.key}
                    r={radius}
                    stroke={slice.color}
                    strokeDasharray={dash}
                    strokeLinecap="butt"
                    strokeWidth={stroke}
                    transform={`rotate(${rotation} ${size / 2} ${size / 2})`}
                  />
                );
              })
            : null}
        </svg>
        <div className={styles.center}>
          <b>{centerValue}</b>
          <small>{centerLabel}</small>
        </div>
      </div>

      <ul className={styles.legend}>
        {slices.map((slice) => (
          <li key={slice.key}>
            <i style={{ background: slice.color }} />
            <span>{slice.label}</span>
            <b>{slice.value}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}
