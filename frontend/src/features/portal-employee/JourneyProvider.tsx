"use client";

import { useTranslations } from "next-intl";
import { createContext, useContext, type ReactNode } from "react";

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

  const { items, unread, markRead, markAllRead } = useNotifications(journey.journey, journey.tasks, journey.days, {
    welcomeTitle: t("welcomeTitle"),
    welcomeBody: t("welcomeBody"),
    unlockedTitle: (title) => t("unlockedTitle", { title }),
    unlockedBody: t("unlockedBody"),
    doneTitle: (title) => t("doneTitle", { title }),
    doneBody: t("doneBody"),
    reminderTitle: (day) => t("reminderTitle", { day }),
    reminderBody: (count) => t("reminderBody", { count }),
  });

  return (
    <JourneyContext.Provider value={{ ...journey, notifications: items, unreadCount: unread, markRead, markAllRead }}>
      {children}
    </JourneyContext.Provider>
  );
}

export function useJourney(): JourneyContextValue {
  const value = useContext(JourneyContext);
  if (!value) throw new Error("useJourney must be used inside JourneyProvider");
  return value;
}
