"use client";

import { Check } from "lucide-react";
import { useTranslations } from "next-intl";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";

import styles from "./DayRail.module.scss";
import shared from "./employee.module.scss";
import type { Day } from "./journeyModel";

/**
 * Cây ngày dọc dùng chung cho trang Nhiệm vụ và trang chi tiết việc: mốc Bắt đầu, từng ngày kèm tiến độ, mốc Kết thúc.
 * Ngày đã xong hết hiện dấu tích thay cho số.
 */
export function DayRail({
  days,
  activeStageId,
  onPick,
}: {
  days: Day[];
  activeStageId: number | null;
  onPick: (stageId: number) => void;
}) {
  const t = useTranslations("employee.tasks");

  return (
    <aside className={styles.side}>
      <div className={styles.sideHead}>
        <b>{t("sideTitle")}</b>
        <small>{t("sideHint")}</small>
      </div>

      <div className={styles.timeline}>
        <div className={styles.tlEnd}>
          <span className={`${styles.tlNode} ${styles.tlStart}`}>
            <FlatIcon name="flag" size={16} tone="red" />
          </span>
          <b>{t("start")}</b>
        </div>

        {days.map((day) => (
          <button
            aria-current={day.stageId === activeStageId ? "step" : undefined}
            className={`${styles.tlItem} ${day.stageId === activeStageId ? styles.tlOn : ""}`}
            key={day.stageId}
            onClick={() => onPick(day.stageId)}
            type="button"
          >
            <span className={styles.tlNode}>
              {day.done === day.total && day.total > 0 ? (
                <Check aria-hidden="true" size={14} />
              ) : (
                (/(\d+)/.exec(day.title)?.[1] ?? day.order)
              )}
            </span>
            <span className={styles.tlCard}>
              <span className={styles.tlTitle}>
                <span>{day.title}</span>
                <strong>
                  {day.done}/{day.total}
                </strong>
              </span>
              <span className={shared.meter}>
                <i style={{ width: `${day.pct}%` }} />
              </span>
            </span>
          </button>
        ))}

        <div className={`${styles.tlEnd} ${styles.tlLast}`}>
          <span className={`${styles.tlNode} ${styles.tlFinish}`}>
            <FlatIcon name="award" size={16} tone="violet" />
          </span>
          <b>{t("finish")}</b>
        </div>
      </div>
    </aside>
  );
}
