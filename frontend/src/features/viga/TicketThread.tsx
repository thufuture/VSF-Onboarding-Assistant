"use client";

import { AlertTriangle, CheckCircle2, Send, UserCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Fragment, type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { PortalSelect } from "@/components/portal-select/PortalSelect";
import { vigaApi, VigaError } from "@/features/viga/api";
import { AttachmentList } from "@/features/viga/attachments/AttachmentList";
import { AttachmentPicker } from "@/features/viga/attachments/AttachmentPicker";
import { useAttachments } from "@/features/viga/attachments/useAttachments";
import { notifyTicketsRead } from "@/features/viga/useTicketUnread";
import type { TicketStatusDTO } from "@/features/viga/dto/requestDTO/viga.request";
import type { TicketDetailResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

import styles from "./TicketThread.module.scss";

/** Chu kỳ hỏi lại tin mới của khung đang mở (chưa phải realtime thật: tin hiện sau tối đa vài giây). */
const POLL_MS = 4_000;

export const TICKET_STATUSES: TicketStatusDTO[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];

/** Màu chấm của từng trạng thái trong các ô chọn. */
export const STATUS_TONE = { OPEN: "amber", IN_PROGRESS: "blue", RESOLVED: "green", CLOSED: "slate" } as const;

function formatTime(iso: string): string {
  const date = new Date(iso);
  return `${date.toLocaleDateString("vi-VN")} ${date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
}

function formatClock(iso: string): string {
  return new Date(iso).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function dayKey(iso: string): string {
  return new Date(iso).toDateString();
}

/**
 * Luồng trao đổi một ticket theo kiểu ứng dụng nhắn tin: đầu khung có avatar người ở bên kia, tin của mình nằm bên phải (màu nhấn),
 * tin của người kia bên trái có avatar, ô soạn dạng viên thuốc (Enter để gửi). HR có thêm "Nhận xử lý" và đổi trạng thái ngay
 * trên đầu khung (đóng ticket không đổi task).
 */
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
  const attachments = useAttachments();
  const listRef = useRef<HTMLUListElement>(null);
  const onChangedRef = useRef(onChanged);
  useEffect(() => {
    onChangedRef.current = onChanged;
  }, [onChanged]);

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
        // Mở ticket là đã xem: huy hiệu giảm 1 và chấm "chưa đọc" ở danh sách tắt.
        void vigaApi.markTicketRead(ticketId).then(notifyTicketsRead, () => undefined);
      })
      .catch((caught: unknown) => !cancelled && fail(caught));
    return () => {
      cancelled = true;
    };
  }, [ticketId, fail]);

  // Tin của bên kia tới khi đang mở khung: hỏi lại máy chủ mỗi vài giây (chỉ khi tab đang hiện, không chen lúc đang gửi/lưu).
  // Chỉ cập nhật khi có tin mới hoặc trạng thái đổi, và không đè ô trạng thái/ghi chú HR đang sửa dở.
  const busyRef = useRef(false);
  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);
  const lastSeenRef = useRef<{ id: number; count: number; status: TicketStatusDTO } | null>(null);
  useEffect(() => {
    if (!detail) return;
    const last = detail.messages[detail.messages.length - 1];
    lastSeenRef.current = { id: last?.id ?? 0, count: detail.messages.length, status: detail.ticket.status };
  }, [detail]);
  useEffect(() => {
    let cancelled = false;
    const timer = window.setInterval(() => {
      if (document.hidden || busyRef.current || !lastSeenRef.current) return;
      vigaApi
        .getTicket(ticketId)
        .then((result) => {
          const seen = lastSeenRef.current;
          if (cancelled || busyRef.current || !seen) return;
          const last = result.messages[result.messages.length - 1];
          const changed = (last?.id ?? 0) !== seen.id || result.messages.length !== seen.count || result.ticket.status !== seen.status;
          if (!changed) return;
          setDetail(result);
          if (result.ticket.status !== seen.status) setStatus(result.ticket.status);
          onChangedRef.current();
          void vigaApi.markTicketRead(ticketId).then(notifyTicketsRead, () => undefined);
        })
        .catch(() => undefined);
    }, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [ticketId]);

  // Cuộn tới tin mới nhất khi mở ticket và sau mỗi tin gửi đi; tin của bên kia tới thì chỉ cuộn nếu anh đang ở cuối khung
  // (đang đọc tin cũ ở trên thì không kéo xuống).
  const stickRef = useRef(true);
  const messageCount = detail?.messages.length ?? 0;
  useEffect(() => {
    const list = listRef.current;
    if (list && stickRef.current) list.scrollTop = list.scrollHeight;
  }, [messageCount]);

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
    stickRef.current = true;
    await run(() => vigaApi.addTicketMessage(ticketId, { body: reply.trim(), attachment_ids: attachments.ids }));
    setReply("");
    attachments.reset();
  }

  function onReplyKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  if (!detail) {
    return <p className={styles.faint}>{errorKey ? t(errorKey) : t("loading")}</p>;
  }
  const { ticket, messages } = detail;
  const closed = ticket.status === "CLOSED";
  // Người ở đầu bên kia: HR thấy nhân viên đã gửi, nhân viên thấy HR phụ trách (chưa ai nhận thì thấy tên phòng ban).
  const peerName = staff ? ticket.requester_name : (ticket.assigned_hr_name ?? ticket.team_name);

  return (
    <section aria-label={ticket.subject} className={styles.thread}>
      <header className={styles.head}>
        <div className={styles.headMain}>
          <span className={styles.headAvatar}>
            <PersonAvatar name={peerName} sizePx={44} />
          </span>
          <div className={styles.headText}>
            <h3>{peerName}</h3>
            <p title={ticket.subject}>
              <b>{ticket.subject}</b>
              <span>
                {staff ? `${ticket.team_name} · ` : ""}
                {formatTime(ticket.created_at)}
                {ticket.related_task_title ? ` · ${t("relatedTask", { title: ticket.related_task_title })}` : ""}
              </span>
            </p>
            {staff && ticket.assigned_hr_name ? (
              <p className={styles.assignee}>
                <UserCheck aria-hidden="true" size={12} />
                <span>{t("assigned", { name: ticket.assigned_hr_name })}</span>
              </p>
            ) : null}
          </div>
          {staff ? null : (
            <span className={styles.chip} data-status={ticket.status}>
              {t(`status.${ticket.status}`)}
            </span>
          )}
        </div>

        {staff ? (
          <div className={styles.tools}>
            {!ticket.assigned_hr_name ? (
              <button className={styles.claim} disabled={busy} onClick={() => run(() => vigaApi.claimTicket(ticketId))} type="button">
                <UserCheck aria-hidden="true" size={14} /> {t("claim")}
              </button>
            ) : null}
            <PortalSelect
              ariaLabel={t("statusLabel")}
              className={styles.statusPick}
              onChange={(next) => setStatus(next as TicketStatusDTO)}
              options={TICKET_STATUSES.map((value) => ({ value, label: t(`status.${value}`), tone: STATUS_TONE[value] }))}
              pill
              value={status ?? ticket.status}
            />
            <input
              aria-label={t("noteLabel")}
              className={styles.noteInput}
              maxLength={2000}
              onChange={(event) => setNote(event.target.value)}
              placeholder={t("noteLabel")}
              value={note}
            />
            <button
              className={styles.save}
              disabled={busy || (status === ticket.status && note === (ticket.resolution_note ?? ""))}
              onClick={() =>
                run(() => vigaApi.setTicketStatus(ticketId, { status: status ?? ticket.status, resolution_note: note || null }))
              }
              type="button"
            >
              {t("saveStatus")}
            </button>
            <small className={styles.hint}>{t("taskUnchanged")}</small>
          </div>
        ) : null}
      </header>

      {errorKey ? (
        <p className={styles.error} role="alert">
          <AlertTriangle aria-hidden="true" size={13} /> {t(errorKey)}
        </p>
      ) : null}

      <ul
        className={styles.messages}
        onScroll={(event) => {
          const list = event.currentTarget;
          stickRef.current = list.scrollHeight - list.scrollTop - list.clientHeight < 80;
        }}
        ref={listRef}
      >
        {messages.map((message, index) => {
          const previous = messages[index - 1];
          const next = messages[index + 1];
          const sameRun = (other: typeof message | undefined) =>
            other !== undefined &&
            dayKey(other.created_at) === dayKey(message.created_at) &&
            other.mine === message.mine &&
            other.sender_name === message.sender_name;
          const newDay = !previous || dayKey(previous.created_at) !== dayKey(message.created_at);
          const firstOfRun = !sameRun(previous);
          const lastOfRun = !sameRun(next);
          return (
            <Fragment key={message.id}>
              {newDay ? (
                <li aria-hidden="true" className={styles.day}>
                  <span>{new Date(message.created_at).toLocaleDateString("vi-VN")}</span>
                </li>
              ) : null}
              <li className={`${styles.row} ${message.mine ? styles.mine : styles.theirs}`}>
                {message.mine ? null : (
                  <span className={styles.rowAvatar}>{lastOfRun ? <PersonAvatar name={message.sender_name} sizePx={30} /> : null}</span>
                )}
                <div className={styles.stack}>
                  {!message.mine && firstOfRun ? (
                    <b className={styles.sender}>
                      {message.sender_name}
                      {message.sender_role !== "USER" ? <i>{t("staffTag")}</i> : null}
                    </b>
                  ) : null}
                  <div className={styles.bubble} data-first={firstOfRun} data-last={lastOfRun}>
                    <p>{message.body}</p>
                    <AttachmentList attachments={message.attachments ?? []} />
                  </div>
                  {lastOfRun ? <small>{formatClock(message.created_at)}</small> : null}
                </div>
              </li>
            </Fragment>
          );
        })}
      </ul>

      {ticket.resolution_note ? (
        <p className={styles.resolution}>
          <CheckCircle2 aria-hidden="true" size={14} /> {t("resolution", { note: ticket.resolution_note })}
        </p>
      ) : null}

      {closed ? (
        <p className={styles.closed}>{t("closedNote")}</p>
      ) : (
        <form className={styles.reply} onSubmit={sendReply}>
          <AttachmentPicker attachments={attachments} compact />
          <textarea
            aria-label={t("replyLabel")}
            maxLength={4000}
            onChange={(event) => setReply(event.target.value)}
            onKeyDown={onReplyKey}
            placeholder={t("replyPlaceholder")}
            rows={1}
            value={reply}
          />
          <button
            aria-label={t("send")}
            className={styles.sendBtn}
            disabled={busy || attachments.uploading || !reply.trim()}
            title={t("send")}
            type="submit"
          >
            <Send aria-hidden="true" size={17} />
          </button>
        </form>
      )}
    </section>
  );
}
