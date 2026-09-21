"use client";

import { ArrowRightIcon, BookIcon } from "@primer/octicons-react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { useSession } from "@/features/auth/SessionProvider";

import styles from "./ChatShell.module.scss";

const SUGGESTION_KEYS = ["firstDay", "equipment", "leave", "contact"] as const;
type SuggestionKey = (typeof SUGGESTION_KEYS)[number];

// `suggestion` null nghĩa là câu hỏi tự gõ: dữ liệu minh họa chưa có căn cứ nên trợ lý nói thẳng thay vì đoán.
type Turn = { id: number; question: string; suggestion: SuggestionKey | null };

/**
 * Vỏ chat dùng dữ liệu minh họa: câu trả lời cố định theo câu hỏi gợi ý, câu hỏi khác nhận "chưa có nguồn".
 * Chưa gọi backend; Phase 2-E nối `POST /api/v1/chat/ask` (câu trả lời có nguồn dẫn thật).
 */
export function ChatShell() {
  const t = useTranslations("chat");
  const { user } = useSession();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");

  function ask(question: string, suggestion: SuggestionKey | null) {
    const text = question.trim();
    if (!text) return;
    setTurns((current) => [...current, { id: current.length + 1, question: text, suggestion }]);
    setDraft("");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    ask(draft, null);
  }

  return (
    <main className={styles.main}>
      <div className={styles.column}>
        <section className={styles.greeting}>
          <h1>{t("greeting", { name: user.display_name })}</h1>
          <p>{t("intro")}</p>
        </section>

        <p className={styles.notice} role="note">
          {t("demoNotice")}
        </p>

        <ol aria-label={t("conversation")} className={styles.thread}>
          {turns.map((turn) => (
            <li key={turn.id}>
              <p className={styles.question}>{turn.question}</p>
              <div className={styles.answer}>
                {turn.suggestion ? (
                  <>
                    <p>{t(`suggestions.${turn.suggestion}.answer`)}</p>
                    <p className={styles.source}>
                      <BookIcon aria-hidden="true" size={14} />
                      <span>{t("sourceLabel")}</span>
                      <strong>{t(`suggestions.${turn.suggestion}.source`)}</strong>
                    </p>
                  </>
                ) : (
                  <p>{t("noSource")}</p>
                )}
              </div>
            </li>
          ))}
        </ol>

        <section aria-label={t("suggestionsLabel")} className={styles.suggestions}>
          <h2>{t("suggestionsTitle")}</h2>
          <div>
            {SUGGESTION_KEYS.map((key) => (
              <button key={key} onClick={() => ask(t(`suggestions.${key}.question`), key)} type="button">
                {t(`suggestions.${key}.question`)}
              </button>
            ))}
          </div>
        </section>

        <form className={styles.composer} onSubmit={submit}>
          <input
            aria-label={t("inputLabel")}
            maxLength={500}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t("placeholder")}
            value={draft}
          />
          <button aria-label={t("send")} disabled={!draft.trim()} type="submit">
            <ArrowRightIcon size={18} />
          </button>
        </form>
      </div>
    </main>
  );
}
