"use client";

import { useEffect, useRef, useState } from "react";

import { portalHrApi } from "@/features/portal-hr/api";
import type { JobResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

const POLL_MS = 1000;
const MAX_CONSECUTIVE_ERRORS = 5;

export function isJobFinished(job: JobResponseDTO | null): boolean {
  return job !== null && (job.status === "SUCCEEDED" || job.status === "FAILED");
}

/** Hỏi tiến độ một việc nền mỗi ~1 giây (đơn giản, chạy qua mọi proxy); dừng khi job kết thúc hoặc rời trang. */
export function useJob(
  jobId: number | null,
  onDone?: (job: JobResponseDTO) => void,
): { job: JobResponseDTO | null; lost: boolean } {
  // Trạng thái gắn với đúng `jobId` đã hỏi: đổi job thì kết quả cũ tự không còn khớp, không cần đặt lại trong effect.
  const [state, setState] = useState<{ forId: number; job: JobResponseDTO | null; lost: boolean } | null>(null);
  const doneRef = useRef(onDone);
  useEffect(() => {
    doneRef.current = onDone;
  });

  useEffect(() => {
    if (jobId === null) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let errors = 0;

    async function tick() {
      try {
        const next = await portalHrApi.getJob(jobId as number);
        if (cancelled) return;
        errors = 0;
        setState({ forId: jobId as number, job: next, lost: false });
        if (isJobFinished(next)) {
          doneRef.current?.(next);
          return;
        }
      } catch {
        if (cancelled) return;
        errors += 1;
        if (errors >= MAX_CONSECUTIVE_ERRORS) {
          setState((current) => ({ forId: jobId as number, job: current?.forId === jobId ? current.job : null, lost: true }));
          return;
        }
      }
      timer = setTimeout(tick, POLL_MS);
    }

    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  const current = state !== null && state.forId === jobId ? state : null;
  return { job: current?.job ?? null, lost: current?.lost ?? false };
}

/** Các job kích hoạt tài liệu đang chạy (để bảng Tài liệu hiện "Đang xử lý 45%"); tự dừng khi không còn job nào. */
export function useActiveActivations(
  enabled: boolean,
  onFinished?: () => void,
): { jobs: JobResponseDTO[]; refresh: () => void } {
  const [jobs, setJobs] = useState<JobResponseDTO[]>([]);
  const [nonce, setNonce] = useState(0);
  const finishedRef = useRef(onFinished);
  useEffect(() => {
    finishedRef.current = onFinished;
  });
  const knownRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function tick() {
      let keepGoing = true;
      try {
        const active = await portalHrApi.listActiveJobs("ACTIVATE_VERSION");
        if (cancelled) return;
        const currentIds = new Set(active.map((job) => job.id));
        const finished = [...knownRef.current].some((id) => !currentIds.has(id));
        knownRef.current = currentIds;
        setJobs(active);
        if (finished) finishedRef.current?.();
        keepGoing = active.length > 0;
      } catch {
        keepGoing = false;
      }
      if (keepGoing && !cancelled) timer = setTimeout(tick, POLL_MS);
    }

    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [enabled, nonce]);

  return { jobs, refresh: () => setNonce((n) => n + 1) };
}
