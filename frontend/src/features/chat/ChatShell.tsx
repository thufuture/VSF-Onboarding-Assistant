"use client";

import {
  ArrowUp,
  Briefcase,
  CalendarDays,
  FileText,
  Laptop,
  Plus,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { useSession } from "@/features/auth/SessionProvider";

import styles from "./ChatShell.module.scss";

const SUGGESTIONS: { key: "firstDay" | "equipment" | "leave" | "contact"; icon: LucideIcon }[] = [
  { key: "firstDay", icon: Briefcase },
  { key: "equipment", icon: Laptop },
  { key: "leave", icon: CalendarDays },
  { key: "contact", icon: Users },
];
type SuggestionKey = (typeof SUGGESTIONS)[number]["key"];

/** Thời gian giả lập "đang tìm nguồn" trước khi hiện câu trả lời minh họa. */
export const MOCK_DELAY_MS = 700;
const MAX_ROWS_HEIGHT = 168;

// `suggestion` null nghĩa là câu hỏi tự gõ: dữ liệu minh họa chưa có căn cứ nên trợ lý nói thẳng thay vì đoán.
type Turn = { id: number; question: string; suggestion: SuggestionKey | null };

/**
 * Trang chat của nhân sự mới theo bố cục chat của Ralion: tiêu đề và phạm vi hỏi ở trên, cột hội thoại giữa, ô nhập
 * cố định ở dưới. Dùng dữ liệu minh họa: câu trả lời cố định theo câu hỏi gợi ý, câu khác nhận "chưa có nguồn".
 * Chưa gọi backend; Phase 2-E nối `POST /api/v1/chat/ask` (câu trả lời có nguồn dẫn thật).
 */
export function ChatShell() {
  const t = useTranslations("chat");
  const { user } = useSession();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState<Turn | null>(null);
  const [draft, setDraft] = useState("");
  const [openSource, setOpenSource] = useState<number | null>(null);
  const timer = useRef<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);

  useEffect(() => () => window.clearTimeout(timer.current ?? undefined), []);

  // Chỉ cuộn xuống khi đã có hội thoại; màn chào giữ nguyên ở đầu (kể cả trên màn hình thấp).
  useEffect(() => {
    if (turns.length === 0 && !pending) return;
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns, pending]);

  // Ô nhập tự cao theo nội dung, tối đa vài dòng rồi cuộn.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_ROWS_HEIGHT)}px`;
  }, [draft]);

  function ask(question: string, suggestion: SuggestionKey | null) {
    const text = question.trim();
    if (!text || pending) return;
    const turn: Turn = { id: nextId.current++, question: text, suggestion };
    setPending(turn);
    setDraft("");
    timer.current = window.setTimeout(() => {
      setTurns((current) => [...current, turn]);
      setPending(null);
    }, MOCK_DELAY_MS);
  }

  function reset() {
    window.clearTimeout(timer.current ?? undefined);
    setTurns([]);
    setPending(null);
    setOpenSource(null);
    inputRef.current?.focus();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    ask(draft, null);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter gửi, Shift+Enter xuống dòng; không gửi khi đang gõ bộ gõ tiếng Việt (IME).
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      ask(draft, null);
    }
  }

  const empty = turns.length === 0 && !pending;
  const shown = pending ? [...turns, pending] : turns;

  return (
    <div className={styles.chat}>
      <div className={styles.scroll}>
        <div className={styles.column}>
          {empty ? null : (
            <button className={styles.newChat} onClick={reset} type="button">
              <Plus aria-hidden="true" size={15} />
              {t("newConversation")}
            </button>
          )}
          {empty ? (
            <section className={styles.empty}>
              <span aria-hidden="true" className={styles.emptyMark}>
                <Sparkles size={26} />
              </span>
              <h2>{t("greeting", { name: user.display_name })}</h2>
              <p>{t("intro")}</p>
              <p className={styles.notice} role="note">
                {t("demoNotice")}
              </p>
              <div aria-label={t("suggestionsLabel")} className={styles.cards} role="group">
                {SUGGESTIONS.map(({ key, icon: Icon }) => (
                  <button className={styles.card} key={key} onClick={() => ask(t(`suggestions.${key}.question`), key)} type="button">
                    <span aria-hidden="true" className={styles.cardIcon}>
                      <Icon size={18} />
                    </span>
                    <span className={styles.cardText}>
                      <b>{t(`suggestions.${key}.title`)}</b>
                      <span>{t(`suggestions.${key}.question`)}</span>
                    </span>
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <ol aria-label={t("conversation")} className={styles.thread}>
              {shown.map((turn) => {
                const answered = turn !== pending;
                return (
                  <li className={styles.turn} key={turn.id}>
                    <p className={styles.question}>{turn.question}</p>
                    <div className={styles.reply}>
                      <span aria-hidden="true" className={styles.replyMark}>
                        <Sparkles size={15} />
                      </span>
                      {answered ? (
                        <article className={styles.answer}>
                          {turn.suggestion ? (
                            <>
                              <p>{t(`suggestions.${turn.suggestion}.answer`)}</p>
                              <div className={styles.sources}>
                                <span>{t("sourceLabel")}</span>
                                <button
                                  aria-expanded={openSource === turn.id}
                                  className={styles.chip}
                                  onClick={() => setOpenSource(openSource === turn.id ? null : turn.id)}
                                  type="button"
                                >
                                  <FileText aria-hidden="true" size={13} />
                                  {t(`suggestions.${turn.suggestion}.source`)}
                                </button>
                              </div>
                              {openSource === turn.id ? (
                                <blockquote className={styles.excerpt}>
                                  <small>{t("excerptLabel")}</small>
                                  {t(`suggestions.${turn.suggestion}.excerpt`)}
                                </blockquote>
                              ) : null}
                            </>
                          ) : (
                            <p>{t("noSource")}</p>
                          )}
                        </article>
                      ) : (
                        <div aria-live="polite" className={styles.thinking} role="status">
                          <span aria-hidden="true" className={styles.dots}>
                            <i />
                            <i />
                            <i />
                          </span>
                          {t("checking")}
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className={styles.dock}>
        <form className={styles.composer} onSubmit={submit}>
          <textarea
            aria-label={t("inputLabel")}
            maxLength={2000}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder={t("placeholder")}
            ref={inputRef}
            rows={1}
            value={draft}
          />
          <div className={styles.composerFoot}>
            <span className={styles.hint}>{t("keyboardHint")}</span>
            <button aria-label={t("send")} className={styles.send} disabled={!draft.trim() || pending !== null} type="submit">
              <ArrowUp aria-hidden="true" size={18} />
            </button>
          </div>
        </form>
        <p className={styles.disclaimer}>{t("disclaimer")}</p>
      </div>
    </div>
  );
}
