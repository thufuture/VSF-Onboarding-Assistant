"use client";

import { useTranslations } from "next-intl";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { vigaApi } from "@/features/viga/api";
import type { TicketSummaryResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

import { useNotifications, type Notification } from "./notifications";
import { summarizeNotice } from "./changeModel";
import { isActionable, useJourneyNotices } from "./useJourneyNotices";
import { useMyJourney } from "./useMyJourney";

type JourneyContextValue = ReturnType<typeof useMyJourney> &
  ReturnType<typeof useJourneyNotices> & {
  /** Mã việc (của chính nhân viên) đang có chỉnh sửa chờ xem: để gắn nhãn "Có chỉnh sửa" ở danh sách và trang việc. */
  changedTaskIds: Map<number, number>;
  notifications: Notification[];
  unreadCount: number;
  markRead: (id: string) => void;
  markAllRead: () => void;
};

const JourneyContext = createContext<JourneyContextValue | null>(null);

/** Nạp lộ trình một lần cho cả khu nhân viên: mọi trang và cả chuông thông báo trên thanh tiêu đề dùng chung dữ liệu này. */
export function JourneyProvider({ children }: { children: ReactNode }) {
  const journey = useMyJourney();
  const changes = useJourneyNotices(journey.reload);
  const t = useTranslations("employee.notifications");
  const tickets = useMyTicketReplies();
  // Ticket HR đã trả lời: mỗi tin mới của HR là một thông báo mới (id gắn với số tin để tin sau lại hiện chưa đọc).
  const ticketItems = useMemo(
    () =>
      tickets
        .filter((ticket) => ticket.last_sender_is_staff)
        .map((ticket) => ({
          id: `ticket-${ticket.id}-${ticket.message_count}`,
          kind: "ticket" as const,
          taskId: null,
          href: `/me/tickets?ticket=${ticket.id}`,
          title: t("ticketTitle", { subject: ticket.subject }),
          body: t("ticketBody"),
          at: ticket.updated_at,
        })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tickets],
  );

  // Lộ trình có thay đổi do HR cập nhật: MỖI lần cập nhật một ngày là MỘT thông báo (không phải mỗi việc một cái). Bấm vào thì mở
  // hộp thoại "đã đổi gì"; chưa mở thì còn chưa đọc (đã đọc lưu ở máy chủ).
  const { notices, markNoticeRead } = changes;
  const changeItems = useMemo(
    () =>
      notices
        .map((notice) => {
          const summary = summarizeNotice(notice.changes);
          const needs = summary.review.length;
          if (needs === 0 && notice.read_at) return null;
          return {
            id: `change-${notice.id}`,
            kind: "change" as const,
            taskId: null,
            noticeId: notice.id,
            title: notice.new_stage
              ? t("newStageTitle", { stage: notice.stage_title })
              : t("changeTitle", { stage: notice.stage_title }),
            body: notice.new_stage
              ? t("newStageBody", { count: summary.added.length })
              : needs > 0
                ? t("changeBody", { count: needs })
                : t("changeAutoBody"),
            at: notice.created_at,
            read: notice.read_at !== null,
          };
        })
        .filter((item): item is NonNullable<typeof item> => item !== null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [notices],
  );

  const changedTaskIds = useMemo(() => {
    const map = new Map<number, number>();
    for (const notice of notices)
      for (const change of notice.changes)
        if (isActionable(change) && change.employee_task_id !== null) map.set(change.employee_task_id, change.id);
    return map;
  }, [notices]);

  const { items, unread, markRead: markLocalRead, markAllRead: markAllLocalRead } = useNotifications(journey.journey, journey.tasks, journey.days, {
    welcomeTitle: t("welcomeTitle"),
    welcomeBody: t("welcomeBody"),
    unlockedTitle: (title) => t("unlockedTitle", { title }),
    unlockedBody: t("unlockedBody"),
    doneTitle: (title) => t("doneTitle", { title }),
    doneBody: t("doneBody"),
    reminderTitle: (day) => t("reminderTitle", { day }),
    reminderBody: (count) => t("reminderBody", { count }),
  }, [...changeItems, ...ticketItems]);

  const markRead = (id: string) => {
    if (id.startsWith("change-")) void markNoticeRead(Number(id.slice("change-".length)));
    else markLocalRead(id);
  };
  const markAllRead = () => {
    markAllLocalRead();
    for (const item of changeItems) if (!item.read) void markNoticeRead(Number(item.id.slice("change-".length)));
  };

  return (
    <JourneyContext.Provider
      value={{ ...journey, ...changes, changedTaskIds, notifications: items, unreadCount: unread, markRead, markAllRead }}
    >
      {children}
    </JourneyContext.Provider>
  );
}

const TICKET_POLL_MS = 60_000;

/** Ticket của chính nhân viên (để chuông báo khi HR trả lời); hỏi lại mỗi phút, lỗi thì giữ danh sách cũ. */
function useMyTicketReplies(): TicketSummaryResponseDTO[] {
  const [tickets, setTickets] = useState<TicketSummaryResponseDTO[]>([]);
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const rows = await vigaApi.listMyTickets();
        if (!cancelled) setTickets(rows);
      } catch {
        /* giữ danh sách cũ */
      }
    }
    void load();
    const timer = setInterval(load, TICKET_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);
  return tickets;
}

export function useJourney(): JourneyContextValue {
  const value = useContext(JourneyContext);
  if (!value) throw new Error("useJourney must be used inside JourneyProvider");
  return value;
}
