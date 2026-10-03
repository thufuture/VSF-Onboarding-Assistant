"use client";

import { useTranslations } from "next-intl";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { vigaApi } from "@/features/viga/api";
import type { TicketSummaryResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

import { useNotifications, type Notification } from "./notifications";
import { useMyJourney } from "./useMyJourney";

type JourneyContextValue = ReturnType<typeof useMyJourney> & {
  notifications: Notification[];
  unreadCount: number;
  markRead: (id: string) => void;
  markAllRead: () => void;
};

const JourneyContext = createContext<JourneyContextValue | null>(null);

/** Nạp lộ trình một lần cho cả khu nhân viên: mọi trang và cả chuông thông báo trên thanh tiêu đề dùng chung dữ liệu này. */
export function JourneyProvider({ children }: { children: ReactNode }) {
  const journey = useMyJourney();
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

  const { items, unread, markRead, markAllRead } = useNotifications(journey.journey, journey.tasks, journey.days, {
    welcomeTitle: t("welcomeTitle"),
    welcomeBody: t("welcomeBody"),
    unlockedTitle: (title) => t("unlockedTitle", { title }),
    unlockedBody: t("unlockedBody"),
    doneTitle: (title) => t("doneTitle", { title }),
    doneBody: t("doneBody"),
    reminderTitle: (day) => t("reminderTitle", { day }),
    reminderBody: (count) => t("reminderBody", { count }),
  }, ticketItems);

  return (
    <JourneyContext.Provider value={{ ...journey, notifications: items, unreadCount: unread, markRead, markAllRead }}>
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
