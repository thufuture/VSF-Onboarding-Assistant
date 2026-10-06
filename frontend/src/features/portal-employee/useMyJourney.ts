"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PortalError, portalHrApi } from "@/features/portal-hr/api";
import type { EmployeeJourneyResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { buildDays, progressOf } from "./journeyModel";

/**
 * - `needsCreate`: HR chưa thêm lộ trình cho nhân viên (lộ trình không tự tạo khi mở trang, chỉ HR thêm);
 * - `noJourney`: chưa có nhóm hoặc chưa có bản nào được áp dụng nên chưa tạo được;
 * - `unavailable`: lỗi khác.
 */
export type JourneyProblem = "needsCreate" | "noJourney" | "unavailable";

function problemOf(error: unknown): JourneyProblem {
  if (error instanceof PortalError) {
    if (error.apiCode === "NO_JOURNEY") return "needsCreate";
    if (error.apiCode === "NO_TEAM_ASSIGNED" || error.apiCode === "NO_JOURNEY_TEMPLATE") return "noJourney";
  }
  return "unavailable";
}

/** Lộ trình RIÊNG của chính nhân viên (bản sao do HR thêm, có hiệu lực ngay) kèm ngày, tiến độ và thao tác hoàn thành task. */
export function useMyJourney() {
  const [journey, setJourney] = useState<EmployeeJourneyResponseDTO | null>(null);
  const [problem, setProblem] = useState<JourneyProblem | null>(null);
  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);

  const reload = useCallback(async () => {
    try {
      setJourney(await portalHrApi.getMyJourney());
      setProblem(null);
    } catch (caught) {
      setProblem(problemOf(caught));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .getMyJourney()
      .then((result) => {
        if (!cancelled) setJourney(result);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setProblem(problemOf(caught));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /** Trả `true` khi hoàn thành được; sau đó nạp lại để các task được mở khóa hiện ngay. */
  const complete = useCallback(
    async (taskId: number): Promise<boolean> => {
      setBusyTaskId(taskId);
      try {
        await portalHrApi.completeTask(taskId);
        await reload();
        return true;
      } catch {
        return false;
      } finally {
        setBusyTaskId(null);
      }
    },
    [reload],
  );

  const tasks = useMemo(() => journey?.tasks ?? [], [journey]);
  const days = useMemo(() => buildDays(tasks), [tasks]);
  const progress = useMemo(() => progressOf(tasks), [tasks]);
  const loading = journey === null && problem === null;

  return { journey, tasks, days, progress, problem, loading, busyTaskId, complete, reload };
}
