"use client";

import { Search, SearchX } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { foldText } from "@/components/text/foldText";
import { vigaApi } from "@/features/viga/api";
import type { TicketStatusDTO } from "@/features/viga/dto/requestDTO/viga.request";
import type { TicketSummaryResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

import styles from "./TicketBoard.module.scss";
import { TICKET_STATUSES, TicketThread } from "./TicketThread";

// Mỗi trạng thái một biểu tượng và một màu riêng để nhìn danh sách là biết ngay ticket nào cần xử lý.
const STATUS_ICON: Record<TicketStatusDTO, { icon: FlatIconName; tone: FlatTone }> = {
  OPEN: { icon: "alert", tone: "amber" },
  IN_PROGRESS: { icon: "clock", tone: "blue" },
  RESOLVED: { icon: "check", tone: "green" },
  CLOSED: { icon: "flag", tone: "slate" },
};

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
          <select
            aria-label={t("filterLabel")}
            className={styles.select}
            onChange={(event) => setFilter(event.target.value as TicketStatusDTO | "ALL")}
            value={filter}
          >
            {(["ALL", ...TICKET_STATUSES] as const).map((key) => (
              <option key={key} value={key}>
                {key === "ALL" ? t("filterAll") : t(`status.${key}`)} ({counts[key]})
              </option>
            ))}
          </select>
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
                const visual = STATUS_ICON[row.status];
                return (
                  <li key={row.id}>
                    <button
                      className={`${styles.item} ${row.id === selectedId ? styles.itemOn : ""}`}
                      data-status={row.status}
                      onClick={() => setSelectedId(row.id)}
                      type="button"
                    >
                      <span className={styles.itemIcon}>
                        <FlatIcon name={visual.icon} size={22} tone={visual.tone} />
                      </span>
                      <span className={styles.itemBody}>
                        <span className={styles.top}>
                          <b>{row.subject}</b>
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
    </div>
  );
}
