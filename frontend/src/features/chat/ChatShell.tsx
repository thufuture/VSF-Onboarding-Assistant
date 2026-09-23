"use client";

import {
  ArrowUp,
  Briefcase,
  CalendarDays,
  ExternalLink,
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
import { chatApi, ChatError } from "@/features/chat/api";
import type { ClaimResponseDTO, SourceResponseDTO } from "@/features/chat/dto/responseDTO/chat.response";
import { DocumentModal } from "@/features/chat/DocumentModal";
import { useRouter } from "@/i18n/navigation";

import styles from "./ChatShell.module.scss";

const SUGGESTIONS: { key: "firstDay" | "equipment" | "leave" | "contact"; icon: LucideIcon }[] = [
  { key: "firstDay", icon: Briefcase },
  { key: "equipment", icon: Laptop },
  { key: "leave", icon: CalendarDays },
  { key: "contact", icon: Users },
];

const MAX_ROWS_HEIGHT = 168;

type Turn =
  | { id: number; question: string; status: "pending" }
  | { id: number; question: string; status: "done"; claims: ClaimResponseDTO[] }
  | { id: number; question: string; status: "error"; errorCode: "unauthorized" | "unavailable" | "network" };

/**
 * Trang chat của nhân sự mới: tiêu đề và phạm vi hỏi ở trên, cột hội thoại giữa, ô nhập cố định ở dưới.
 * Gọi `POST /api/v1/chat/ask` thật (Phase 2-E) — một câu hỏi của người dùng có thể bị backend tách thành
 * nhiều `claims[]` độc lập (câu hỏi nhiều ý, ví dụ "mai tôi đi làm mấy giờ, mentor tôi là ai").
 */
export function ChatShell() {
  const t = useTranslations("chat");
  const { user } = useSession();
  const router = useRouter();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [openSource, setOpenSource] = useState<string | null>(null);
  const [openDocument, setOpenDocument] = useState<SourceResponseDTO | null>(null);
  const [inFlight, setInFlight] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);

  // Chỉ cuộn xuống khi đã có hội thoại; màn chào giữ nguyên ở đầu (kể cả trên màn hình thấp).
  useEffect(() => {
    if (turns.length === 0) return;
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns]);

  // Ô nhập tự cao theo nội dung, tối đa vài dòng rồi cuộn.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_ROWS_HEIGHT)}px`;
  }, [draft]);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || inFlight) return;
    const id = nextId.current++;
    setInFlight(true);
    setDraft("");
    setTurns((current) => [...current, { id, question: text, status: "pending" }]);

    try {
      const response = await chatApi.ask(text);
      setTurns((current) =>
        current.map((turn) => (turn.id === id ? { id, question: text, status: "done", claims: response.claims } : turn)),
      );
    } catch (caught) {
      if (caught instanceof ChatError && caught.code === "unauthorized") {
        router.replace("/login");
        return;
      }
      const errorCode = caught instanceof ChatError ? caught.code : "network";
      setTurns((current) => current.map((turn) => (turn.id === id ? { id, question: text, status: "error", errorCode } : turn)));
    } finally {
      setInFlight(false);
    }
  }

  function reset() {
    setTurns([]);
    setOpenSource(null);
    inputRef.current?.focus();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(draft);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter gửi, Shift+Enter xuống dòng; không gửi khi đang gõ bộ gõ tiếng Việt (IME).
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void ask(draft);
    }
  }

  const empty = turns.length === 0;

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
              <h2>{t("greeting", { name: user.display_name })}</h2>
              <p>{t("intro")}</p>
              <div aria-label={t("suggestionsLabel")} className={styles.cards} role="group">
                {SUGGESTIONS.map(({ key, icon: Icon }) => (
                  <button className={styles.card} key={key} onClick={() => void ask(t(`suggestions.${key}.question`))} type="button">
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
              {turns.map((turn) => (
                <li className={styles.turn} key={turn.id}>
                  <p className={styles.question}>{turn.question}</p>
                  <div className={styles.reply}>
                    <span aria-hidden="true" className={styles.replyMark}>
                      <Sparkles size={15} />
                    </span>
                    {turn.status === "pending" ? (
                      <div aria-live="polite" className={styles.thinking} role="status">
                        <span aria-hidden="true" className={styles.dots}>
                          <i />
                          <i />
                          <i />
                        </span>
                        {t("checking")}
                      </div>
                    ) : turn.status === "error" ? (
                      <article className={styles.answer}>
                        <p>{t(`error.${turn.errorCode}`)}</p>
                      </article>
                    ) : (
                      <article className={styles.answer}>
                        {turn.claims.length === 0 ? (
                          <p>{t("noSource")}</p>
                        ) : (
                          turn.claims.map((claim, index) => {
                            const sourceId = `${turn.id}-${index}`;
                            return (
                              <div className={styles.claim} key={sourceId}>
                                {claim.response_type === "ANSWER" && claim.source ? (
                                  <>
                                    <p>{claim.text}</p>
                                    <div className={styles.sources}>
                                      <span>{t("sourceLabel")}</span>
                                      <button
                                        aria-expanded={openSource === sourceId}
                                        className={styles.chip}
                                        onClick={() => setOpenSource(openSource === sourceId ? null : sourceId)}
                                        type="button"
                                      >
                                        <FileText aria-hidden="true" size={13} />
                                        {claim.source.document_title} ({claim.source.version_label})
                                      </button>
                                      <button
                                        className={styles.chip}
                                        onClick={() => setOpenDocument(claim.source)}
                                        type="button"
                                      >
                                        <ExternalLink aria-hidden="true" size={13} />
                                        {t("openDocument")}
                                      </button>
                                    </div>
                                    {openSource === sourceId && claim.quote ? (
                                      <blockquote className={styles.excerpt}>
                                        <small>{t("excerptLabel")}</small>
                                        {claim.quote}
                                      </blockquote>
                                    ) : null}
                                  </>
                                ) : (
                                  <p>{t("noSource")}</p>
                                )}
                              </div>
                            );
                          })
                        )}
                      </article>
                    )}
                  </div>
                </li>
              ))}
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
            <button aria-label={t("send")} className={styles.send} disabled={!draft.trim() || inFlight} type="submit">
              <ArrowUp aria-hidden="true" size={18} />
            </button>
          </div>
        </form>
        <p className={styles.disclaimer}>{t("disclaimer")}</p>
      </div>

      {openDocument ? (
        <DocumentModal
          documentTitle={openDocument.document_title}
          documentUrl={openDocument.document_url}
          onClose={() => setOpenDocument(null)}
          sectionHeading={openDocument.section_heading}
          versionId={openDocument.version_id}
          versionLabel={openDocument.version_label}
        />
      ) : null}
    </div>
  );
}
