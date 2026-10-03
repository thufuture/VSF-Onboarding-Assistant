"use client";

import { History, Loader2, Maximize2, MessageSquarePlus, Pencil, Send, Sparkles, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { VigaAvatar } from "@/components/avatar/VigaAvatar";
import { PortalModal } from "@/components/portal-modal/PortalModal";
import { useSession } from "@/features/auth/SessionProvider";
import { SendToHrModal } from "@/features/viga/SendToHrModal";
import { relatedTaskId, useVigaChat } from "@/features/viga/useVigaChat";
import { VigaReply } from "@/features/viga/VigaReply";
import { useRouter } from "@/i18n/navigation";

import { givenName } from "./journeyModel";
import styles from "./VigaPanel.module.scss";
import { useVigaPanel } from "./vigaPanelStore";

/**
 * Ngăn trò chuyện với Viga — cột bên phải vùng làm việc như view `chat` của prototype v15 (mở ra thì trang co lại,
 * không che nội dung). Nối API thật `/viga/ask`: công cụ lộ trình, hỏi đáp tài liệu có nguồn, đường thoát và gợi ý gửi HR.
 * Hội thoại lưu trên máy chủ: mở lại, đổi tên, xóa, mở cuộc mới (mục 6.2). Nút "Mở rộng" đưa sang trang đầy đủ `/me/viga`.
 */
export function VigaPanel() {
  const t = useTranslations("employee.viga");
  const router = useRouter();
  const { user } = useSession();
  const { open, question, seq, close } = useVigaPanel();
  const chat = useVigaChat();
  const { turns, conversationId, draft, setDraft, busy, history, renaming, setRenaming, report, setReport } = chat;
  const [infoOpen, setInfoOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const answered = useRef(0);
  const { send } = chat;

  // Nút "Hỏi Viga về việc này" ở trang chi tiết gửi sẵn câu hỏi qua kho trạng thái; `seq` để hỏi lại cùng câu vẫn chạy.
  useEffect(() => {
    if (!question || seq === answered.current) return;
    answered.current = seq;
    void send(question);
  }, [question, seq, send]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function toggleHistory() {
    const next = !historyOpen;
    setHistoryOpen(next);
    if (next && history === null) await chat.loadHistory();
  }

  async function openConversation(id: number) {
    if (await chat.openConversation(id)) setHistoryOpen(false);
  }

  function newConversation() {
    chat.newConversation();
    setHistoryOpen(false);
    inputRef.current?.focus();
  }

  /** Mở trang Viga đầy đủ, giữ nguyên cuộc trò chuyện đang mở. */
  function expand() {
    close();
    router.push(conversationId ? { pathname: "/me/viga", query: { c: String(conversationId) } } : "/me/viga");
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  const quick = ["q1", "q2", "q3", "q4"] as const;
  const canDo = ["a1", "a2", "a3"] as const;
  const cannotDo = ["b1", "b2", "b3"] as const;

  return (
    <>
      <aside aria-label={t("title")} className={`${styles.panel} ${open ? styles.panelOpen : ""}`} hidden={!open}>
        <header className={styles.head}>
          <VigaAvatar sizePx={38} />
          <div>
            <b>{t("title")}</b>
            <small>{t("subtitle")}</small>
          </div>
          <button
            aria-label={t("history.new")}
            className={styles.iconButton}
            onClick={newConversation}
            title={t("history.new")}
            type="button"
          >
            <MessageSquarePlus aria-hidden="true" size={15} />
          </button>
          <button
            aria-expanded={historyOpen}
            aria-label={t("history.title")}
            className={styles.iconButton}
            onClick={toggleHistory}
            title={t("history.title")}
            type="button"
          >
            <History aria-hidden="true" size={15} />
          </button>
          <button
            aria-label={t("infoLabel")}
            className={styles.iconButton}
            onClick={() => setInfoOpen(true)}
            title={t("infoLabel")}
            type="button"
          >
            <Sparkles aria-hidden="true" size={15} />
          </button>
          <button
            aria-label={t("expand")}
            className={styles.iconButton}
            onClick={expand}
            title={t("expand")}
            type="button"
          >
            <Maximize2 aria-hidden="true" size={15} />
          </button>
          <button aria-label={t("close")} className={styles.iconButton} onClick={close} type="button">
            <X aria-hidden="true" size={15} />
          </button>
        </header>

        {historyOpen ? (
          <section aria-label={t("history.title")} className={styles.history}>
            <b>{t("history.title")}</b>
            {history === null ? (
              <p className={styles.historyEmpty}>{t("history.loading")}</p>
            ) : history.length === 0 ? (
              <p className={styles.historyEmpty}>{t("history.empty")}</p>
            ) : (
              <ul>
                {history.map((item) => (
                  <li className={item.id === conversationId ? styles.historyOn : ""} key={item.id}>
                    {renaming?.id === item.id ? (
                      <form onSubmit={chat.saveRename}>
                        <input
                          aria-label={t("history.rename")}
                          autoFocus
                          maxLength={120}
                          onChange={(event) => setRenaming({ id: item.id, title: event.target.value })}
                          value={renaming.title}
                        />
                      </form>
                    ) : (
                      <button className={styles.historyOpen} onClick={() => openConversation(item.id)} type="button">
                        <span>{item.title}</span>
                        <small>{new Date(item.updated_at).toLocaleDateString("vi-VN")}</small>
                      </button>
                    )}
                    <button
                      aria-label={t("history.rename")}
                      className={styles.historyIcon}
                      onClick={() => setRenaming({ id: item.id, title: item.title })}
                      title={t("history.rename")}
                      type="button"
                    >
                      <Pencil aria-hidden="true" size={12} />
                    </button>
                    <button
                      aria-label={t("history.delete")}
                      className={styles.historyIcon}
                      onClick={() => void chat.removeConversation(item.id)}
                      title={t("history.delete")}
                      type="button"
                    >
                      <Trash2 aria-hidden="true" size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <small className={styles.historyNote}>{t("history.retention")}</small>
          </section>
        ) : null}

        <div className={styles.body}>
          {turns.length === 0 ? (
            <div className={styles.intro}>
              <div className={styles.row}>
                <VigaAvatar sizePx={26} />
                <p className={styles.bot}>{t("hello", { name: givenName(user.display_name) })}</p>
              </div>
              <div className={styles.quickColumn}>
                {quick.map((key) => (
                  <button key={key} onClick={() => void send(t(`quick.${key}`))} type="button">
                    {t(`quick.${key}`)}
                  </button>
                ))}
              </div>
              <button className={styles.infoLink} onClick={() => setInfoOpen(true)} type="button">
                <Sparkles aria-hidden="true" size={13} /> {t("infoLink")}
              </button>
            </div>
          ) : (
            turns.map((turn) => (
              <div className={styles.turn} key={turn.id}>
                {turn.question ? <p className={styles.user}>{turn.question}</p> : null}
                <div className={styles.row}>
                  <VigaAvatar sizePx={26} />
                  <div className={styles.bot}>
                    {turn.reply ? (
                      <VigaReply
                        onReport={() => turn.reply && setReport({ turnId: turn.id, question: turn.question, reply: turn.reply })}
                        reply={turn.reply}
                        sentTicketId={turn.ticketId}
                      />
                    ) : turn.error ? (
                      <p className={styles.errorText} role="alert">
                        {turn.error}
                      </p>
                    ) : (
                      <p className={styles.thinking} role="status">
                        <Loader2 aria-hidden="true" className={styles.spin} size={14} /> {t("thinking")}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        <div className={styles.foot}>
          {turns.length > 0 ? (
            <div className={styles.quick}>
              {quick.map((key) => (
                <button disabled={busy} key={key} onClick={() => void send(t(`quick.${key}`))} type="button">
                  {t(`quick.${key}`)}
                </button>
              ))}
            </div>
          ) : null}
          <form className={styles.form} onSubmit={onSubmit}>
            <input
              aria-label={t("inputLabel")}
              maxLength={2000}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={t("placeholder")}
              ref={inputRef}
              value={draft}
            />
            <button aria-label={t("send")} disabled={!draft.trim() || busy} type="submit">
              <Send aria-hidden="true" size={15} />
            </button>
          </form>
        </div>
      </aside>

      {report ? (
        <SendToHrModal
          conversationId={conversationId}
          employeeTaskId={relatedTaskId(report.reply)}
          onClose={() => setReport(null)}
          onSent={(ticket) => {
            chat.markTicketSent(report.turnId, ticket.id);
            setReport(null);
          }}
          question={report.question}
        />
      ) : null}

      {infoOpen ? (
        <PortalModal
          closeLabel={t("close")}
          icon={Sparkles}
          onClose={() => setInfoOpen(false)}
          subtitle={t("subtitle")}
          title={t("infoTitle")}
          wide
        >
          <div className={styles.info}>
            <p>{t("infoIntro")}</p>
            <div className={styles.infoCols}>
              <section>
                <h3>{t("canTitle")}</h3>
                <ul>
                  {canDo.map((key) => (
                    <li key={key}>{t(`can.${key}`)}</li>
                  ))}
                </ul>
              </section>
              <section>
                <h3>{t("cannotTitle")}</h3>
                <ul>
                  {cannotDo.map((key) => (
                    <li key={key}>{t(`cannot.${key}`)}</li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </PortalModal>
      ) : null}
    </>
  );
}
