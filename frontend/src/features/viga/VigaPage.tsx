"use client";

import { Minimize2, MessageSquarePlus, Pencil, Send, Sparkles, Trash2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, type FormEvent } from "react";

import { VigaAvatar } from "@/components/avatar/VigaAvatar";
import { useSession } from "@/features/auth/SessionProvider";
import { givenName } from "@/features/portal-employee/journeyModel";
import { SendToHrModal } from "@/features/viga/SendToHrModal";
import { relatedTaskId, useVigaChat } from "@/features/viga/useVigaChat";
import { VigaReply } from "@/features/viga/VigaReply";
import { useRouter } from "@/i18n/navigation";

import { WaveText } from "@/components/thinking/WaveText";
import styles from "./VigaPage.module.scss";

const QUICK = ["q1", "q2", "q3", "q4"] as const;

/**
 * Trang Viga đầy đủ của nhân viên (kiểu ChatGPT): cột trái là lịch sử hội thoại, giữa là khung trò chuyện rộng. Dùng chung kho
 * hội thoại, câu trả lời có nguồn, 👍/👎 và gửi HR với ngăn Viga ở bên phải; mở bằng nút "Mở rộng" của ngăn (`?c=` giữ cuộc đang mở).
 */
export function VigaPage() {
  const t = useTranslations("employee.viga");
  const { user } = useSession();
  const router = useRouter();
  const requested = Number(useSearchParams().get("c"));
  const chat = useVigaChat();
  const { turns, conversationId, draft, setDraft, busy, history, renaming, setRenaming, report, setReport } = chat;
  const { loadHistory, openConversation } = chat;
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const opened = useRef(false);

  // Nạp danh sách lúc vào trang và nạp lại mỗi khi bị đánh dấu cũ (sau khi hỏi, cuộc trò chuyện mới/cập nhật).
  const historyStale = history === null;
  useEffect(() => {
    if (historyStale) void loadHistory();
  }, [historyStale, loadHistory]);

  // Mở đúng cuộc trò chuyện được chuyển sang từ ngăn Viga (chỉ một lần khi vào trang).
  useEffect(() => {
    if (opened.current || !Number.isInteger(requested) || requested <= 0) return;
    opened.current = true;
    void openConversation(requested);
  }, [requested, openConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    void chat.send(draft);
  }

  function collapse() {
    router.push("/me");
  }

  return (
    <div className={styles.page}>
      <div className={styles.layout}>
        <aside aria-label={t("page.listTitle")} className={styles.side}>
          <button className={styles.newChat} onClick={chat.newConversation} type="button">
            <MessageSquarePlus aria-hidden="true" size={16} /> {t("history.new")}
          </button>
          <b className={styles.sideTitle}>{t("page.listTitle")}</b>
          <div className={styles.list}>
            {history === null ? (
              <p className={styles.faint}>{t("history.loading")}</p>
            ) : history.length === 0 ? (
              <p className={styles.faint}>{t("page.emptyList")}</p>
            ) : (
              <ul>
                {history.map((item) => (
                  <li className={item.id === conversationId ? styles.on : ""} key={item.id}>
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
                      <button className={styles.open} onClick={() => void chat.openConversation(item.id)} type="button">
                        <span>{item.title}</span>
                        <small>{new Date(item.updated_at).toLocaleDateString("vi-VN")}</small>
                      </button>
                    )}
                    <button
                      aria-label={t("history.rename")}
                      className={styles.icon}
                      onClick={() => setRenaming({ id: item.id, title: item.title })}
                      title={t("history.rename")}
                      type="button"
                    >
                      <Pencil aria-hidden="true" size={12} />
                    </button>
                    <button
                      aria-label={t("history.delete")}
                      className={styles.icon}
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
          </div>
          <small className={styles.note}>{t("history.retention")}</small>
        </aside>

        <section aria-label={t("page.title")} className={styles.chat}>
          <header className={styles.head}>
            <VigaAvatar sizePx={36} />
            <div>
              <h1>{t("page.title")}</h1>
              <small>{t("subtitle")}</small>
            </div>
            <button className={styles.collapse} onClick={collapse} type="button">
              <Minimize2 aria-hidden="true" size={14} /> {t("page.collapse")}
            </button>
          </header>

          <div className={styles.messages}>
            <div className={styles.column}>
              {turns.length === 0 ? (
                <div className={styles.hello}>
                  <VigaAvatar sizePx={56} />
                  <h2>{t("page.greetingTitle")}</h2>
                  <p>{t("hello", { name: givenName(user.display_name) })}</p>
                  <small>{t("page.greetingHint")}</small>
                  <div className={styles.quick}>
                    {QUICK.map((key) => (
                      <button key={key} onClick={() => void chat.send(t(`quick.${key}`))} type="button">
                        <Sparkles aria-hidden="true" size={14} /> {t(`quick.${key}`)}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                turns.map((turn) => (
                  <div className={styles.turn} key={turn.id}>
                    {turn.question ? <p className={styles.user}>{turn.question}</p> : null}
                    <div className={styles.bot}>
                      <VigaAvatar sizePx={30} />
                      <div className={styles.botBody}>
                        {turn.reply ? (
                          <VigaReply
                            onReport={() =>
                              turn.reply && setReport({ turnId: turn.id, question: turn.question, reply: turn.reply })
                            }
                            reply={turn.reply}
                            sentTicketId={turn.ticketId}
                          />
                        ) : turn.error ? (
                          <p className={styles.error} role="alert">
                            {turn.error}
                          </p>
                        ) : (
                          <p className={styles.thinking}>
                            <WaveText text={t("thinking")} />
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <form className={styles.composer} onSubmit={submit}>
            <div className={styles.composerIn}>
              <textarea
                aria-label={t("inputLabel")}
                maxLength={2000}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void chat.send(draft);
                  }
                }}
                placeholder={t("placeholder")}
                ref={inputRef}
                rows={1}
                value={draft}
              />
              <button aria-label={t("send")} disabled={!draft.trim() || busy} type="submit">
                <Send aria-hidden="true" size={16} />
              </button>
            </div>
          </form>
        </section>
      </div>

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
    </div>
  );
}
