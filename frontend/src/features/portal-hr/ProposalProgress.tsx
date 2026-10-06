"use client";

import { Check, Circle, Loader2, Minus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { JobProgress } from "@/components/job-progress/JobProgress";
import type { JobResponseDTO, JobStepDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./ProposalProgress.module.scss";

/** Không báo "còn bao lâu" khi mới chạy (số đo chưa đáng tin) hoặc sắp xong. */
const ETA_MIN_PERCENT = 8;

/** Số giây còn lại ước tính theo tốc độ đã chạy; `null` nếu chưa đủ dữ liệu. */
export function estimateRemainingSeconds(percent: number, elapsedSeconds: number): number | null {
  if (percent < ETA_MIN_PERCENT || percent >= 99 || elapsedSeconds < 3) return null;
  return Math.max(1, Math.round((elapsedSeconds * (100 - percent)) / percent));
}

/** Đồng hồ chạy mỗi giây, bám theo `elapsed_seconds` backend trả về (không tự bịa số giây). */
function useElapsed(job: JobResponseDTO | null): number {
  const anchor = useRef<{ base: number; at: number } | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const base = job?.elapsed_seconds ?? null;
  const finished = job?.status === "SUCCEEDED" || job?.status === "FAILED";

  useEffect(() => {
    if (base === null) {
      anchor.current = null;
      return;
    }
    anchor.current = { base, at: Date.now() };
    const tick = () => {
      const current = anchor.current;
      if (current) setElapsed(current.base + (finished ? 0 : Math.floor((Date.now() - current.at) / 1000)));
    };
    tick();
    if (finished) return;
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [base, finished]);

  return base === null ? 0 : elapsed;
}

function StepIcon({ status }: { status: string }) {
  if (status === "done") return <Check aria-hidden="true" size={13} />;
  if (status === "running") return <Loader2 aria-hidden="true" className={styles.spin} size={13} />;
  if (status === "skipped") return <Minus aria-hidden="true" size={13} />;
  return <Circle aria-hidden="true" size={11} />;
}

function StepRow({ step }: { step: JobStepDTO }) {
  const t = useTranslations("portalHr.progress");
  const showCount = step.total > 1 && step.status !== "pending" && step.status !== "skipped";
  return (
    <li data-status={step.status}>
      <i>
        <StepIcon status={step.status} />
      </i>
      <span>{t(`steps.${step.key}`)}</span>
      {showCount ? <small>{`${step.done}/${step.total}`}</small> : null}
      {step.status === "skipped" ? <small>{t("skipped")}</small> : null}
      {step.seconds !== null && (step.status === "done" || step.status === "running") ? (
        <small>{t("seconds", { seconds: Math.round(step.seconds) })}</small>
      ) : null}
    </li>
  );
}

/** Tiến độ tạo task bằng AI từ đầu đến cuối: phần trăm thật, từng bước, thời gian đã chạy và còn lại, hàng đợi, từng tài liệu. */
export function ProposalProgress({
  job,
  lost,
  creating,
}: {
  job: JobResponseDTO | null;
  lost: boolean;
  /** Đang tạo task thật sau khi HR duyệt: `done/total`. */
  creating: { done: number; total: number } | null;
}) {
  const t = useTranslations("portalHr.progress");
  const elapsed = useElapsed(job);
  const percent = job?.progress_percent ?? 0;
  const steps = job?.progress?.steps ?? [];
  const documents = job?.progress?.documents ?? [];
  const waiting = job !== null && job.status === "PENDING";
  const remaining = waiting ? null : estimateRemainingSeconds(percent, elapsed);

  // Tên tab hiện phần trăm để HR chuyển tab làm việc khác vẫn theo dõi được.
  useEffect(() => {
    if (job === null || creating !== null) return;
    const original = document.title;
    document.title = `${Math.round(percent)}% · ${original.replace(/^\d+% · /, "")}`;
    return () => {
      document.title = original.replace(/^\d+% · /, "");
    };
  }, [job, percent, creating]);

  if (creating !== null) {
    const value = creating.total > 0 ? (creating.done / creating.total) * 100 : 0;
    return (
      <div className={styles.box} data-testid="creating-progress">
        <JobProgress percent={value} stage={t("creating", { done: creating.done, total: creating.total })} state="running" />
      </div>
    );
  }

  return (
    <div className={styles.box} data-testid="proposal-progress">
      <JobProgress
        percent={percent}
        stage={waiting ? t("queued") : (job?.stage ?? t("waiting"))}
        state={waiting ? "pending" : "running"}
      />
      {waiting && (job?.queue_ahead ?? 0) > 0 ? (
        <p className={styles.queue}>{t("queueAhead", { count: job?.queue_ahead ?? 0 })}</p>
      ) : null}
      {steps.length > 0 ? (
        <ol className={styles.steps}>
          {steps.map((step) => (
            <StepRow key={step.key} step={step} />
          ))}
        </ol>
      ) : null}
      {documents.length > 1 ? (
        <ul className={styles.docs}>
          {documents.map((doc) => (
            <li data-failed={doc.failed ? "true" : undefined} key={doc.version_id}>
              <span>{doc.title}</span>
              <b>{doc.percent}%</b>
            </li>
          ))}
        </ul>
      ) : null}
      <p className={styles.time}>
        {job?.elapsed_seconds != null ? t("elapsed", { seconds: elapsed }) : null}
        {remaining !== null ? ` · ${t("remaining", { seconds: remaining })}` : null}
      </p>
      {lost ? <small className={styles.lost}>{t("lost")}</small> : null}
    </div>
  );
}
