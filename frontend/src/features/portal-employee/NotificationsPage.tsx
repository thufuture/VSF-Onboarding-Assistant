"use client";

import { Bell, Check, ChevronRight, Clock, LockOpen, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useRouter } from "@/i18n/navigation";

import shared from "./employee.module.scss";
import { useSession } from "@/features/auth/SessionProvider";

import { useJourney } from "./JourneyProvider";
import styles from "./NotificationsPage.module.scss";
import { PageHero } from "./PageHero";
import type { NotificationKind } from "./notifications";

const ICONS: Record<NotificationKind, typeof Bell> = {
  unlocked: LockOpen,
  done: Check,
  reminder: Clock,
  welcome: Sparkles,
};

/** "Thông báo" (view `notifs` của v15): nhắc việc trong portal. Nội dung suy ra từ lộ trình thật; đã đọc lưu ở trình duyệt. */
export function EmployeeNotificationsPage() {
  const t = useTranslations("employee.notifications");
  const { user } = useSession();
  const router = useRouter();
  const { notifications, unreadCount, markRead, markAllRead, loading } = useJourney();
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const shown = notifications.filter((item) => (filter === "unread" ? !item.read : true));

  return (
    <>
      <PageHero
        avatarName={user.display_name}
        compact
        subtitle={t("subtitle")}
        title={t("title")}
      />

      <div className={shared.container}>
        <div className={styles.bar}>
          <div className={styles.chips}>
            <button
              className={`${styles.chip} ${filter === "all" ? styles.chipOn : ""}`}
              onClick={() => setFilter("all")}
              type="button"
            >
              {t("filterAll", { count: notifications.length })}
            </button>
            <button
              className={`${styles.chip} ${filter === "unread" ? styles.chipOn : ""}`}
              onClick={() => setFilter("unread")}
              type="button"
            >
              {t("filterUnread", { count: unreadCount })}
            </button>
          </div>
          <button className={shared.btnGhost} disabled={unreadCount === 0} onClick={markAllRead} type="button">
            <Check aria-hidden="true" size={14} /> {t("markAll")}
          </button>
        </div>

        {loading ? (
          <div className={styles.list}>
            {[0, 1, 2].map((i) => (
              <div className={shared.skeleton} key={i} style={{ height: 78, marginBottom: 8 }} />
            ))}
          </div>
        ) : shown.length === 0 ? (
          <div className={`${shared.card} ${shared.empty}`}>
            <Bell aria-hidden="true" size={32} />
            <b>{t("emptyTitle")}</b>
            <span>{t("emptyBody")}</span>
          </div>
        ) : (
          <ul className={`${shared.card} ${shared.rise} ${styles.list}`}>
            {shown.map((item) => {
              const Icon = ICONS[item.kind];
              return (
                <li key={item.id}>
                  <button
                    className={`${styles.item} ${item.read ? "" : styles.unread}`}
                    onClick={() => {
                      markRead(item.id);
                      if (item.taskId) router.push({ pathname: "/me/tasks", query: { task: item.taskId } });
                    }}
                    type="button"
                  >
                    <span className={`${styles.icon} ${styles[item.kind]}`}>
                      <Icon aria-hidden="true" size={16} />
                    </span>
                    <span className={styles.text}>
                      <span className={styles.meta}>
                        <b>{t(`kind.${item.kind}`)}</b>
                        {item.at ? <span>· {new Date(item.at).toLocaleDateString()}</span> : null}
                        {item.read ? null : <i className={styles.dot} />}
                      </span>
                      <span className={styles.itemTitle}>{item.title}</span>
                      <span className={styles.itemBody}>{item.body}</span>
                    </span>
                    {item.taskId ? <ChevronRight aria-hidden="true" className={styles.go} size={16} /> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </>
  );
}
