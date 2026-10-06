"use client";

import { Plus, Search, SearchX } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { PortalSelect } from "@/components/portal-select/PortalSelect";
import { foldText } from "@/components/text/foldText";
import { vigaApi } from "@/features/viga/api";
import type { TicketStatusDTO } from "@/features/viga/dto/requestDTO/viga.request";
import type { TicketSummaryResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";
import { SendToHrModal } from "@/features/viga/SendToHrModal";

import styles from "./TicketBoard.module.scss";
import { STATUS_TONE, TICKET_STATUSES, TicketThread } from "./TicketThread";
import { TICKETS_READ_EVENT } from "./useTicketUnread";

/**
 * Danh sách ticket bên trái, luồng trao đổi bên phải. Trên danh sách có ô tìm kiếm (tiêu đề; HR còn tìm được theo tên và email
 * người gửi) và ô chọn lọc theo trạng thái. `staff`: HR/Admin thấy hàng đợi của phòng ban (nhận xử lý, đổi trạng thái);
 * nhân viên chỉ thấy ticket của mình và trả lời được.
 */
export function TicketBoard({ staff, initialTicketId = null }: { staff: boolean; initialTicketId?: number | null }) {
  const t = useTranslations("viga.ticket");
  const [tickets, setTickets] = useState<TicketSummaryResponseDTO[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(initialTicketId);
  const [filter, setFilter] = useState<TicketStatusDTO | "ALL">("ALL");
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);

  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    let cancelled = false;
    (staff ? vigaApi.listStaffTickets() : vigaApi.listMyTickets())
      .then((rows) => {
        if (cancelled) return;
        setTickets(rows);
        setFailed(false);
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        setTickets((current) => current ?? []);
      });
    return () => {
      cancelled = true;
    };
  }, [staff, reloadKey]);

  // Danh sách tự cập nhật: ngay khi mở một ticket (chấm chưa đọc tắt) và mỗi 30 giây (ticket, tin mới của bên kia).
  useEffect(() => {
    window.addEventListener(TICKETS_READ_EVENT, reload);
    const timer = window.setInterval(() => {
      if (!document.hidden) reload();
    }, 30_000);
    return () => {
      window.removeEventListener(TICKETS_READ_EVENT, reload);
      window.clearInterval(timer);
    };
  }, [reload]);

  const counts = useMemo(() => {
    const result: Record<string, number> = { ALL: tickets?.length ?? 0 };
    for (const status of TICKET_STATUSES) result[status] = tickets?.filter((row) => row.status === status).length ?? 0;
    return result;
  }, [tickets]);

  const needle = foldText(query.trim());
  const shown = (tickets ?? []).filter((row) => {
    if (filter !== "ALL" && row.status !== filter) return false;
    if (!needle) return true;
    const haystack = [row.subject, row.related_task_title ?? "", ...(staff ? [row.requester_name, row.requester_email, row.team_name] : [])];
    return foldText(haystack.join(" ")).includes(needle);
  });
  const total = tickets?.length ?? 0;

  return (
    <div className={styles.board}>
      <aside aria-label={t("listLabel")} className={styles.list}>
        {!staff ? (
          <button className={styles.create} onClick={() => setCreating(true)} type="button">
            <Plus aria-hidden="true" size={15} /> {t("create")}
          </button>
        ) : null}
        <div className={styles.toolbar}>
          <label className={styles.search}>
            <Search aria-hidden="true" size={14} />
            <input
              aria-label={t("searchLabel")}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t(staff ? "searchPlaceholderStaff" : "searchPlaceholderMine")}
              type="search"
              value={query}
            />
          </label>
          <PortalSelect
            ariaLabel={t("filterLabel")}
            className={styles.select}
            onChange={(next) => setFilter(next as TicketStatusDTO | "ALL")}
            options={(["ALL", ...TICKET_STATUSES] as const).map((key) => ({
              value: key,
              label: `${key === "ALL" ? t("filterAll") : t(`status.${key}`)} (${counts[key]})`,
              tone: key === "ALL" ? undefined : STATUS_TONE[key],
            }))}
            value={filter}
          />
        </div>

        {failed ? <p className={styles.error}>{t("errors.generic")}</p> : null}
        {tickets === null ? (
          <p className={styles.faint}>{t("loading")}</p>
        ) : total === 0 ? (
          <div className={styles.empty}>
            <FlatIcon name={staff ? "lifebuoy" : "chat"} size={56} tone={staff ? "teal" : "indigo"} />
            <b>{t(staff ? "emptyStaff" : "emptyMine")}</b>
            <small>{t(staff ? "emptyStaffHint" : "emptyMineHint")}</small>
          </div>
        ) : shown.length === 0 ? (
          <div className={styles.empty}>
            <SearchX aria-hidden="true" size={34} />
            <b>{t("noMatch")}</b>
            <small>{t("noMatchHint")}</small>
          </div>
        ) : (
          <>
            <ul>
              {shown.map((row) => {
                return (
                  <li key={row.id}>
                    <button
                      className={`${styles.item} ${row.id === selectedId ? styles.itemOn : ""} ${row.unread ? styles.itemUnread : ""}`}
                      data-status={row.status}
                      data-unread={row.unread ? "true" : undefined}
                      onClick={() => setSelectedId(row.id)}
                      type="button"
                    >
                      <span className={styles.itemIcon}>
                        <PersonAvatar name={staff ? row.requester_name : (row.assigned_hr_name ?? row.team_name)} sizePx={38} />
                      </span>
                      <span className={styles.itemBody}>
                        <span className={styles.top}>
                          <b>{row.subject}</b>
                          {row.unread ? <span aria-label={t("unread")} className={styles.dot} role="status" /> : null}
                          <i className={styles.chip} data-status={row.status}>
                            {t(`status.${row.status}`)}
                          </i>
                        </span>
                        <small>
                          {staff ? `${row.requester_name} · ` : ""}
                          {new Date(row.updated_at).toLocaleDateString("vi-VN")} ·{" "}
                          {t("messages", { count: row.message_count })}
                        </small>
                        {staff ? <small className={styles.email}>{row.requester_email}</small> : null}
                        {!staff && row.last_sender_is_staff ? <em>{t("hrReplied")}</em> : null}
                        {staff && !row.assigned_hr_name && row.status === "OPEN" ? <em>{t("unclaimed")}</em> : null}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            <p className={styles.count}>{t("showing", { shown: shown.length, total })}</p>
          </>
        )}
      </aside>

      <div className={styles.detail}>
        {selectedId === null ? (
          <div className={styles.pickEmpty}>
            <FlatIcon name="chat" size={72} tone="indigo" />
            <b>{t("pick")}</b>
            <small>{t("pickHint")}</small>
          </div>
        ) : (
          <TicketThread key={selectedId} onChanged={reload} staff={staff} ticketId={selectedId} />
        )}
      </div>
      {creating ? (
        <SendToHrModal
          conversationId={null}
          employeeTaskId={null}
          fresh
          onClose={() => setCreating(false)}
          onSent={(ticket) => {
            setCreating(false);
            setFilter("ALL");
            setQuery("");
            setSelectedId(ticket.id);
            reload();
          }}
          question=""
        />
      ) : null}
    </div>
  );
}
