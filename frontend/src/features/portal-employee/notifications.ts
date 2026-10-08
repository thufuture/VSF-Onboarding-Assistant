"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

import type { EmployeeJourneyResponseDTO, EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { stateOf, type Day } from "./journeyModel";

// Thông báo THẬT (lộ trình có thay đổi, ticket được HR trả lời) đến từ máy chủ qua `extras`, đã đọc lưu ở máy chủ.
// Ngoài ra danh sách có vài dòng SUY RA từ chính lộ trình (việc làm được ngay, việc đã xong, nhắc việc, lời chào): chỉ là gợi
// ý trạng thái, mỗi loại GỘP thành một dòng và KHÔNG tính vào số chưa đọc trên chuông (nếu không số đó bằng số việc của bạn).
export type NotificationKind = "unlocked" | "done" | "reminder" | "welcome" | "ticket" | "change";

export type Notification = {
  id: string;
  kind: NotificationKind;
  taskId: number | null;
  /** Đường dẫn mở khi bấm (thông báo ticket); thông báo việc dùng `taskId`. */
  href?: string | null;
  /** Thông báo lộ trình có thay đổi: bấm thì mở hộp thoại "đã đổi gì" của thông báo này. */
  noticeId?: number;
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
  unlockedManyTitle: (count: number) => string;
  unlockedManyBody: string;
  doneTitle: (title: string) => string;
  doneBody: string;
  doneManyTitle: (count: number) => string;
  doneManyBody: string;
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

  // Việc làm được ngay và việc đã xong: MỘT dòng cho mỗi loại (một việc thì nêu tên việc, nhiều việc thì nêu số lượng).
  const ready = tasks.filter((row) => stateOf(row) === "ready");
  if (ready.length === 1) {
    const task = ready[0]!;
    items.push({
      id: `unlocked-${task.id}`,
      kind: "unlocked",
      taskId: task.id,
      title: text.unlockedTitle(task.title),
      body: text.unlockedBody,
      at: null,
    });
  } else if (ready.length > 1) {
    items.push({
      id: `unlocked-many-${ready.length}`,
      kind: "unlocked",
      taskId: null,
      href: "/me/tasks",
      title: text.unlockedManyTitle(ready.length),
      body: text.unlockedManyBody,
      at: null,
    });
  }

  const finished = tasks.filter((row) => stateOf(row) === "done");
  if (finished.length === 1) {
    const task = finished[0]!;
    items.push({
      id: `done-${task.id}`,
      kind: "done",
      taskId: task.id,
      title: text.doneTitle(task.title),
      body: text.doneBody,
      at: task.completed_at,
    });
  } else if (finished.length > 1) {
    items.push({
      id: `done-many-${finished.length}`,
      kind: "done",
      taskId: null,
      href: "/me/tasks",
      title: text.doneManyTitle(finished.length),
      body: text.doneManyBody,
      at: finished.map((task) => task.completed_at ?? "").sort().at(-1) || null,
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
    // Dòng suy ra từ lộ trình luôn ở trạng thái đã đọc: không tính vào số chưa đọc của chuông.
    const derived = buildList(journey, tasks, days, text).map((item) => ({ ...item, read: true }));
    const all: (Omit<Notification, "read"> & { read?: boolean })[] = [...extras, ...derived];
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
