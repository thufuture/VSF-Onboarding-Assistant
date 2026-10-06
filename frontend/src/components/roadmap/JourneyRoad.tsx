"use client";

import { Check, Lock } from "lucide-react";
import { useId, useState, type CSSProperties, type ReactNode } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { groupStyle } from "@/components/roadmap/taskGroups";
import type { TaskGroupDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./JourneyRoad.module.scss";

// Hình học roadmap giống trang Quản lý task của HR: canvas cao 470, nút rải đều 6%→94%, độ cao lệch nhẹ như sóng thoải,
// thẻ xen kẽ trên (top 16) / dưới (top 298).
const CANVAS_H = 470;
const CARD_W = 196;
const CARD_H = 138;
const CARD_TOP = 16;
const CARD_BOTTOM = 298;
const NODE = 50;
// Hai thẻ cùng hàng cách nhau 2 bước nút; mỗi bước rộng 0,88·W/(n+1) nên cần W ≥ (n+1)·~128 để thẻ rộng 196 còn hở ≥ 28px.
const MIN_STEP = 130;
const CENTERS = [232, 210, 240, 214, 236, 208, 238, 216, 234, 212, 240, 218];

export type RoadState = "done" | "ready" | "locked";

export type RoadItem = {
  id: number;
  title: string;
  group: TaskGroupDTO | null;
  /** Bỏ trống ở trang HR (chưa có tiến độ); nhân viên có 3 trạng thái. */
  state?: RoadState;
  pill: string;
  chips: { icon: ReactNode; label: string }[];
};

export type RoadAction = { icon: ReactNode; title: string; onClick: () => void; disabled?: boolean; tone?: "danger" | "success" };

type CSSVars = CSSProperties & { "--node"?: string; "--i"?: number; "--end"?: string };

const LOCKED_COLOR = "#8f9bb0";

/**
 * Roadmap sóng ngang dùng chung cho HR (quản lý task) và nhân viên (lộ trình của tôi): đường nhựa mềm, nút tròn có icon nhóm,
 * thẻ có dải màu đầu thẻ, mốc Bắt đầu/Kết thúc nằm trên đường. Nhân viên có thêm trạng thái: đoạn đường đã đi tô xanh lá,
 * nút đã xong có dấu tích, nút đang mở có vòng nhấp nháy, nút bị khóa xám kèm ổ khóa.
 */
export function JourneyRoad({
  items,
  labels,
  onOpen,
  actionsFor,
  onEndClick,
  onReorder,
}: {
  items: RoadItem[];
  labels: { start: string; finish: string; taskNo: (n: string) => string };
  onOpen: (item: RoadItem) => void;
  actionsFor: (item: RoadItem) => RoadAction[];
  onEndClick?: (kind: "start" | "finish") => void;
  /** Có thì thẻ kéo thả được: thả thẻ `fromId` lên thẻ `toId` thì `fromId` nhận vị trí của `toId`. */
  onReorder?: (fromId: number, toId: number) => void;
}) {
  const [dragging, setDragging] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  const clipId = useId().replace(/:/g, "");
  const count = items.length;
  // Điểm 0 = "Bắt đầu", điểm 1..n = task, điểm n+1 = "Kết thúc": cả ba loại đều là nút nằm trên đường.
  const total = count + 2;
  const layout = Array.from({ length: total }, (_, j) => {
    const x = 6 + (j * 88) / (total - 1);
    const center = CENTERS[j % CENTERS.length];
    return { x, center, top: center - NODE / 2, onTop: (j - 1) % 2 === 0 };
  });
  const pts = layout.map((p) => ({ x: p.x * 10, y: p.center }));
  // Đường cong Catmull-Rom qua mọi điểm (toạ độ viewBox 1000 = phần trăm × 10).
  const path = pts
    .map((q, i) => {
      if (i === 0) return `M ${q.x} ${q.y}`;
      const p0 = pts[i - 2] ?? pts[i - 1];
      const p1 = pts[i - 1];
      const p3 = pts[i + 1] ?? q;
      const c1x = p1.x + (q.x - p0.x) / 6;
      const c1y = p1.y + (q.y - p0.y) / 6;
      const c2x = q.x - (p3.x - p1.x) / 6;
      const c2y = q.y - (p3.y - p1.y) / 6;
      return `C ${c1x} ${c1y}, ${c2x} ${c2y}, ${q.x} ${q.y}`;
    })
    .join(" ");

  // Đoạn đã đi: từ "Bắt đầu" tới task xong liên tiếp cuối cùng (cắt theo trục x vì đường luôn đi sang phải).
  const withState = items.some((it) => it.state);
  let doneRun = 0;
  while (doneRun < count && items[doneRun].state === "done") doneRun++;
  const walkedX = doneRun === count && count > 0 ? pts[total - 1].x : pts[doneRun].x;

  const ends = [
    { p: layout[0], kind: "start" as const, tone: "red" as const, flat: "flag" as const, label: labels.start },
    { p: layout[total - 1], kind: "finish" as const, tone: "violet" as const, flat: "award" as const, label: labels.finish },
  ];

  return (
    <div className={styles.roadScroll}>
      <div className={styles.canvas} style={{ height: CANVAS_H, minWidth: Math.max(820, (count + 1) * MIN_STEP) }}>
        <svg aria-hidden="true" className={styles.roadSvg} preserveAspectRatio="none" viewBox={`0 0 1000 ${CANVAS_H}`}>
          <defs>
            <clipPath id={`${clipId}-reveal`}>
              <rect className={styles.reveal} height={CANVAS_H} width="1000" x="0" y="0" />
            </clipPath>
            <clipPath id={`${clipId}-walked`}>
              <rect height={CANVAS_H} width={walkedX} x="0" y="0" />
            </clipPath>
          </defs>
          <g clipPath={`url(#${clipId}-reveal)`}>
            <path className={styles.roadBed} d={path} vectorEffect="non-scaling-stroke" />
            <path className={styles.roadLine} d={path} vectorEffect="non-scaling-stroke" />
            {withState ? (
              <path className={styles.roadWalked} clipPath={`url(#${clipId}-walked)`} d={path} vectorEffect="non-scaling-stroke" />
            ) : null}
            <path className={styles.roadDash} d={path} vectorEffect="non-scaling-stroke" />
          </g>
        </svg>

        {ends.map((end) => (
          <div
            className={`${styles.endNode} ${end.kind === "start" ? styles.endStart : styles.endFinish}`}
            key={end.kind}
            title={end.label}
          >
            <button
              aria-label={end.label}
              className={styles.endCircle}
              disabled={!onEndClick}
              onClick={() => onEndClick?.(end.kind)}
              style={{ left: `calc(${end.p.x}% - 24px)`, top: end.p.center - 24 }}
              type="button"
            >
              <FlatIcon name={end.flat} size={24} tone={end.tone} />
            </button>
            <em style={{ left: `calc(${end.p.x}% - 40px)`, top: end.p.center + 30 }}>{end.label}</em>
          </div>
        ))}

        {items.map((item, i) => {
          const p = layout[i + 1];
          const g = groupStyle(item.group);
          const locked = item.state === "locked";
          const color = locked ? LOCKED_COLOR : g.color;
          const tetherTop = p.onTop ? CARD_TOP + CARD_H : p.top + NODE;
          const tetherHeight = p.onTop ? p.top - (CARD_TOP + CARD_H) : CARD_BOTTOM - (p.top + NODE);
          const actions = actionsFor(item);
          return (
            <article
              className={`${styles.roadItem} ${item.state ? styles[`is_${item.state}`] : ""} ${over === item.id && dragging !== item.id ? styles.dropTarget : ""} ${dragging === item.id ? styles.dragging : ""}`}
              draggable={onReorder ? true : undefined}
              onDragEnd={() => {
                setDragging(null);
                setOver(null);
              }}
              onDragOver={
                onReorder
                  ? (event) => {
                      event.preventDefault();
                      if (over !== item.id) setOver(item.id);
                    }
                  : undefined
              }
              onDragStart={onReorder ? (event) => {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", String(item.id));
                    setDragging(item.id);
                  } : undefined}
              onDrop={
                onReorder
                  ? (event) => {
                      event.preventDefault();
                      if (dragging !== null && dragging !== item.id) onReorder(dragging, item.id);
                      setDragging(null);
                      setOver(null);
                    }
                  : undefined
              }
              key={item.id}
              style={{ "--node": color, "--i": i } as CSSVars}
            >
              <i
                className={`${styles.tether} ${p.onTop ? styles.tetherTop : styles.tetherBottom}`}
                style={{ left: `${p.x}%`, top: tetherTop, height: Math.max(tetherHeight, 0) }}
              />
              <button
                aria-label={item.title}
                className={styles.node}
                onClick={() => onOpen(item)}
                style={{ left: `calc(${p.x}% - ${NODE / 2}px)`, top: p.top, width: NODE, height: NODE }}
                type="button"
              >
                {locked ? <Lock aria-hidden="true" color={LOCKED_COLOR} size={20} /> : <FlatIcon name={g.flat} size={24} tone={g.tone} />}
                {item.state === "done" ? (
                  <i className={`${styles.nodeNum} ${styles.nodeDone}`}>
                    <Check aria-hidden="true" size={12} strokeWidth={3} />
                  </i>
                ) : (
                  <i className={styles.nodeNum}>{i + 1}</i>
                )}
              </button>
              <div
                className={styles.card}
                style={{
                  width: CARD_W,
                  left: `clamp(4px, calc(${p.x}% - ${CARD_W / 2}px), calc(100% - ${CARD_W + 4}px))`,
                  top: p.onTop ? CARD_TOP : CARD_BOTTOM,
                }}
              >
                <div className={styles.cardBand}>
                  <small>
                    <span className={styles.bandIcon}>
                      {locked ? <Lock aria-hidden="true" color={LOCKED_COLOR} size={12} /> : <FlatIcon name={g.flat} size={17} tone={g.tone} />}
                    </span>
                    {labels.taskNo(String(i + 1).padStart(2, "0"))}
                  </small>
                  <span className={styles.bandPill}>{item.pill}</span>
                </div>
                <div className={styles.cardBody}>
                  <h3 title={item.title}>{item.title}</h3>
                  <div className={styles.chips}>
                    {item.chips.map((chip, k) => (
                      <span key={k}>
                        {chip.icon} {chip.label}
                      </span>
                    ))}
                  </div>
                </div>
                <div className={styles.actions}>
                  {actions.map((action, k) => (
                    <button
                      className={action.tone ? styles[action.tone] : undefined}
                      disabled={action.disabled}
                      key={k}
                      onClick={action.onClick}
                      title={action.title}
                      type="button"
                    >
                      {action.icon}
                    </button>
                  ))}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
