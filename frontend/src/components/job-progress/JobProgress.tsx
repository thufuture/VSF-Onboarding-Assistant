"use client";

import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

import styles from "./JobProgress.module.scss";

export type JobProgressState = "pending" | "running" | "done" | "failed";

/** Thanh tiến trình cho việc nền (nạp/kích hoạt tài liệu, tạo task bằng AI): phần trăm thật + tên bước hiện tại. */
export function JobProgress({
  percent,
  stage,
  state,
  compact = false,
}: {
  percent: number;
  stage?: string | null;
  state: JobProgressState;
  compact?: boolean;
}) {
  const value = Math.max(0, Math.min(100, Math.round(percent)));
  const Icon = state === "failed" ? AlertTriangle : state === "done" ? CheckCircle2 : Loader2;
  return (
    <div className={`${styles.wrap} ${compact ? styles.compact : ""}`} data-state={state}>
      <div className={styles.line}>
        <Icon aria-hidden="true" className={state === "running" || state === "pending" ? styles.spin : ""} size={compact ? 12 : 14} />
        <span className={styles.stage}>{stage ?? ""}</span>
        <b>{value}%</b>
      </div>
      <div
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={value}
        className={styles.track}
        role="progressbar"
      >
        <i style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
