"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { portalHrApi } from "@/features/portal-hr/api";
import type {
  ChangePreviewResponseDTO,
  JourneyNoticeResponseDTO,
  TaskChangeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

const POLL_MS = 60_000;

/** Việc đang chờ nhân viên xem (không tính dòng chỉ báo thông tin của việc đã làm bị bỏ). */
export function isActionable(change: TaskChangeResponseDTO): boolean {
  return change.status === "PENDING" && !change.informational;
}

/**
 * Thông báo "lộ trình có thay đổi" từ máy chủ: HR áp dụng bản mới thì lộ trình của nhân viên KHÔNG tự đổi, nhân viên được báo
 * và tự bấm "Cập nhật". Hỏi lại mỗi phút (như ticket); sau mỗi thao tác nạp lại ngay. `onApplied` gọi sau khi cập nhật để
 * lộ trình cũng được nạp lại.
 */
export function useJourneyNotices(onApplied: () => Promise<void> | void) {
  const [allNotices, setNotices] = useState<JourneyNoticeResponseDTO[]>([]);
  const [busyChangeId, setBusyChangeId] = useState<number | null>(null);
  // Thông báo mà mọi thay đổi đã bị bản mới hơn thay thế không còn gì để quyết định: không hiện.
  const notices = useMemo(
    () => allNotices.filter((notice) => notice.changes.some((change) => change.status !== "SUPERSEDED")),
    [allNotices],
  );

  const reload = useCallback(async () => {
    try {
      setNotices(await portalHrApi.listMyJourneyNotices());
    } catch {
      /* giữ danh sách cũ */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const rows = await portalHrApi.listMyJourneyNotices();
        if (!cancelled) setNotices(rows);
      } catch {
        /* giữ danh sách cũ */
      }
    }
    void load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const markNoticeRead = useCallback(
    async (noticeId: number) => {
      try {
        await portalHrApi.markJourneyNoticeRead(noticeId);
        await reload();
      } catch {
        /* không quan trọng: lần sau đọc lại */
      }
    },
    [reload],
  );

  const previewChange = useCallback(
    (changeId: number): Promise<ChangePreviewResponseDTO> => portalHrApi.previewJourneyChange(changeId),
    [],
  );

  const run = useCallback(
    async (changeId: number, action: () => Promise<unknown>): Promise<boolean> => {
      setBusyChangeId(changeId);
      try {
        await action();
        await Promise.all([reload(), onApplied()]);
        return true;
      } catch {
        await reload();
        return false;
      } finally {
        setBusyChangeId(null);
      }
    },
    [reload, onApplied],
  );

  const acceptChange = useCallback(
    (changeId: number) => run(changeId, () => portalHrApi.acceptJourneyChange(changeId)),
    [run],
  );
  const dismissChange = useCallback(
    (changeId: number) => run(changeId, () => portalHrApi.dismissJourneyChange(changeId)),
    [run],
  );
  const acceptAll = useCallback(
    (noticeId: number) => run(-noticeId, () => portalHrApi.acceptAllJourneyChanges(noticeId)),
    [run],
  );

  const pendingCount = useMemo(
    () => notices.reduce((sum, notice) => sum + notice.changes.filter(isActionable).length, 0),
    [notices],
  );

  /** Thay đổi đang chờ theo mã, để trang chi tiết việc tìm đúng thay đổi của việc đang xem. */
  const changeById = useMemo(() => {
    const map = new Map<number, { change: TaskChangeResponseDTO; notice: JourneyNoticeResponseDTO }>();
    for (const notice of notices) for (const change of notice.changes) map.set(change.id, { change, notice });
    return map;
  }, [notices]);

  return {
    notices,
    pendingCount,
    changeById,
    busyChangeId,
    reloadNotices: reload,
    markNoticeRead,
    previewChange,
    acceptChange,
    dismissChange,
    acceptAll,
  };
}
