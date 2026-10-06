"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

import type { EmployeeJourneyResponseDTO, EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { stateOf, type Day } from "./journeyModel";

// Portal chưa có API thông báo (bảng `tickets`/`notifications` chưa có router), nên danh sách này được SUY RA từ
// chính lộ trình thật: việc vừa mở khóa, việc đã xong, việc bắt buộc còn lại. Trạng thái "đã đọc" lưu ở trình duyệt
// của từng người (localStorage), không gửi lên máy chủ.
export type NotificationKind = "unlocked" | "done" | "reminder" | "welcome" | "ticket" | "change";

export type Notification = {
  id: string;
  kind: NotificationKind;
  taskId: number | null;
  /** Đường dẫn mở khi bấm (thông báo ticket); thông báo việc dùng `taskId`. */
  href?: string | null;
  title: string;
  body: string;
  at: string | null;
  read: boolean;
};

const STORAGE_KEY = "vsf-read-notifications";
const listeners = new Set<() => void>();
let memory: string[] | null = null;
const EMPTY: string[] = [];

function readIds(): string[] {
  if (memory) return memory;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    memory = Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    memory = [];
  }
  return memory;
}

function writeIds(ids: string[]): void {
  memory = ids;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Trình duyệt chặn lưu trữ: vẫn đánh dấu đã đọc trong phiên này.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

export type NotificationText = {
  welcomeTitle: string;
  welcomeBody: string;
  unlockedTitle: (title: string) => string;
  unlockedBody: string;
  doneTitle: (title: string) => string;
  doneBody: string;
  reminderTitle: (day: string) => string;
  reminderBody: (count: number) => string;
};

function buildList(
  journey: EmployeeJourneyResponseDTO | null,
  tasks: EmployeeTaskResponseDTO[],
  days: Day[],
  text: NotificationText,
): Omit<Notification, "read">[] {
  if (!journey) return [];
  const items: Omit<Notification, "read">[] = [];

  for (const task of tasks.filter((row) => stateOf(row) === "ready")) {
    items.push({
      id: `unlocked-${task.id}`,
      kind: "unlocked",
      taskId: task.id,
      title: text.unlockedTitle(task.title),
      body: text.unlockedBody,
      at: null,
    });
  }

  for (const task of tasks.filter((row) => stateOf(row) === "done")) {
    items.push({
      id: `done-${task.id}`,
      kind: "done",
      taskId: task.id,
      title: text.doneTitle(task.title),
      body: text.doneBody,
      at: task.completed_at,
    });
  }

  const day = days.find((row) => row.done < row.total);
  if (day) {
    const left = day.tasks.filter((task) => task.required && stateOf(task) !== "done").length;
    if (left > 0) {
      items.push({
        id: `reminder-${day.stageId}-${left}`,
        kind: "reminder",
        taskId: null,
        title: text.reminderTitle(day.title),
        body: text.reminderBody(left),
        at: null,
      });
    }
  }

  items.push({
    id: `welcome-${journey.id}`,
    kind: "welcome",
    taskId: null,
    title: text.welcomeTitle,
    body: text.welcomeBody,
    at: journey.started_at,
  });

  return items;
}

/** Danh sách thông báo suy ra từ lộ trình, kèm số chưa đọc và thao tác đánh dấu đã đọc. */
export function useNotifications(
  journey: EmployeeJourneyResponseDTO | null,
  tasks: EmployeeTaskResponseDTO[],
  days: Day[],
  text: NotificationText,
  extras: (Omit<Notification, "read"> & { read?: boolean })[] = [],
) {
  const readIdList = useSyncExternalStore(subscribe, readIds, () => EMPTY);

  const items = useMemo(() => {
    const read = new Set(readIdList);
    const all: (Omit<Notification, "read"> & { read?: boolean })[] = [...extras, ...buildList(journey, tasks, days, text)];
    return all.map((item) => ({ ...item, read: item.read ?? read.has(item.id) }));
    // `text` là đối tượng dựng lại mỗi lần render nên không đưa vào dependency (nội dung chỉ đổi khi đổi ngôn ngữ).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [journey, tasks, days, readIdList, extras]);

  const markRead = useCallback(
    (id: string) => {
      if (readIds().includes(id)) return;
      writeIds([...readIds(), id]);
    },
    [],
  );

  const markAllRead = useCallback(() => {
    writeIds([...new Set([...readIds(), ...items.map((item) => item.id)])]);
  }, [items]);

  return { items, unread: items.filter((item) => !item.read).length, markRead, markAllRead };
}
