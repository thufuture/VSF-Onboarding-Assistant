"use client";

import { AlertTriangle, CheckCircle2, Send, UserCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { vigaApi, VigaError } from "@/features/viga/api";
import type { TicketStatusDTO } from "@/features/viga/dto/requestDTO/viga.request";
import type { TicketDetailResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

import styles from "./TicketThread.module.scss";

export const TICKET_STATUSES: TicketStatusDTO[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];

function formatTime(iso: string): string {
  const date = new Date(iso);
  return `${date.toLocaleDateString("vi-VN")} ${date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
}

/** Luồng trao đổi một ticket: tin nhắn, ô trả lời; HR thêm "Nhận xử lý" và đổi trạng thái (đóng ticket không đổi task). */
export function TicketThread({
  ticketId,
  staff,
  onChanged,
}: {
  ticketId: number;
  staff: boolean;
  onChanged: () => void;
}) {
  const t = useTranslations("viga.ticket");
  const [detail, setDetail] = useState<TicketDetailResponseDTO | null>(null);
  // Lưu khóa dịch của lỗi, dịch lúc hiển thị: hàm `t` của next-intl đổi tham chiếu mỗi lần render nên không được đưa vào
  // phụ thuộc của effect (sẽ gọi lại API liên tục).
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<TicketStatusDTO | null>(null);
  const [note, setNote] = useState("");

  const fail = useCallback((caught: unknown) => {
    const apiCode = caught instanceof VigaError ? caught.apiCode : null;
    setErrorKey(
      apiCode === "TICKET_CLOSED"
        ? "errors.closed"
        : apiCode === "TICKET_ALREADY_CLAIMED"
          ? "errors.claimed"
          : "errors.generic",
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    vigaApi
      .getTicket(ticketId)
      .then((result) => {
        if (cancelled) return;
        setDetail(result);
        setStatus(result.ticket.status);
        setNote(result.ticket.resolution_note ?? "");
        setErrorKey(null);
      })
      .catch((caught: unknown) => !cancelled && fail(caught));
    return () => {
      cancelled = true;
    };
  }, [ticketId, fail]);

  async function run(action: () => Promise<TicketDetailResponseDTO>) {
    setBusy(true);
    setErrorKey(null);
    try {
      const result = await action();
      setDetail(result);
      setStatus(result.ticket.status);
      onChanged();
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  }

  async function sendReply(event: FormEvent) {
    event.preventDefault();
    if (!reply.trim()) return;
    await run(() => vigaApi.addTicketMessage(ticketId, { body: reply.trim() }));
    setReply("");
  }

  if (!detail) {
    return <p className={styles.faint}>{errorKey ? t(errorKey) : t("loading")}</p>;
  }
  const { ticket, messages } = detail;
  const closed = ticket.status === "CLOSED";

  return (
    <section aria-label={ticket.subject} className={styles.thread}>
      <header className={styles.head}>
        <div>
          <h3>{ticket.subject}</h3>
          <p>
            {staff ? `${ticket.requester_name} · ` : ""}
            {ticket.team_name} · {formatTime(ticket.created_at)}
            {ticket.related_task_title ? ` · ${t("relatedTask", { title: ticket.related_task_title })}` : ""}
          </p>
        </div>
        <span className={styles.chip} data-status={ticket.status}>
          {t(`status.${ticket.status}`)}
        </span>
      </header>

      {ticket.assigned_hr_name ? (
        <p className={styles.assignee}>
          <UserCheck aria-hidden="true" size={13} /> {t("assigned", { name: ticket.assigned_hr_name })}
        </p>
      ) : null}
      {errorKey ? (
        <p className={styles.error} role="alert">
          <AlertTriangle aria-hidden="true" size={13} /> {t(errorKey)}
        </p>
      ) : null}

      <ul className={styles.messages}>
        {messages.map((message) => (
          <li className={message.mine ? styles.mine : ""} key={message.id}>
            <b>
              {message.sender_name}
              {message.sender_role !== "USER" ? <i>{t("staffTag")}</i> : null}
            </b>
            <p>{message.body}</p>
            <small>{formatTime(message.created_at)}</small>
          </li>
        ))}
      </ul>

      {ticket.resolution_note ? (
        <p className={styles.resolution}>
          <CheckCircle2 aria-hidden="true" size={13} /> {t("resolution", { note: ticket.resolution_note })}
        </p>
      ) : null}

      {closed ? (
        <p className={styles.faint}>{t("closedNote")}</p>
      ) : (
        <form className={styles.reply} onSubmit={sendReply}>
          <textarea
            aria-label={t("replyLabel")}
            maxLength={4000}
            onChange={(event) => setReply(event.target.value)}
            placeholder={t("replyPlaceholder")}
            rows={3}
            value={reply}
          />
          <button disabled={busy || !reply.trim()} type="submit">
            <Send aria-hidden="true" size={14} /> {t("send")}
          </button>
        </form>
      )}

      {staff ? (
        <div className={styles.staff}>
          {!ticket.assigned_hr_name ? (
            <button disabled={busy} onClick={() => run(() => vigaApi.claimTicket(ticketId))} type="button">
              <UserCheck aria-hidden="true" size={14} /> {t("claim")}
            </button>
          ) : null}
          <label>
            {t("statusLabel")}
            <select onChange={(event) => setStatus(event.target.value as TicketStatusDTO)} value={status ?? ticket.status}>
              {TICKET_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {t(`status.${value}`)}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.noteField}>
            {t("noteLabel")}
            <input maxLength={2000} onChange={(event) => setNote(event.target.value)} value={note} />
          </label>
          <button
            disabled={busy || (status === ticket.status && note === (ticket.resolution_note ?? ""))}
            onClick={() =>
              run(() => vigaApi.setTicketStatus(ticketId, { status: status ?? ticket.status, resolution_note: note || null }))
            }
            type="button"
          >
            {t("saveStatus")}
          </button>
          <small>{t("taskUnchanged")}</small>
        </div>
      ) : null}
    </section>
  );
}
