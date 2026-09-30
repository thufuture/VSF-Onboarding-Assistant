"use client";

import { Send, Sparkles, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { VigaAvatar } from "@/components/avatar/VigaAvatar";
import { PortalModal } from "@/components/portal-modal/PortalModal";
import { useSession } from "@/features/auth/SessionProvider";
import { useRouter } from "@/i18n/navigation";

import { useJourney } from "./JourneyProvider";
import { givenName } from "./journeyModel";
import styles from "./VigaPanel.module.scss";
import { askViga, type VigaReply } from "./vigaMock";
import { useVigaPanel } from "./vigaPanelStore";

type Turn = { id: number; question: string; reply: VigaReply };

/**
 * Ngăn trò chuyện với Viga — cột bên phải vùng làm việc như view `chat` của prototype v15 (mở ra thì trang co lại,
 * không che nội dung). Bản dựng giao diện: câu trả lời suy ra từ lộ trình thật của người đăng nhập, CHƯA gọi API.
 */
export function VigaPanel() {
  const t = useTranslations("employee.viga");
  const tt = useTranslations("employee.task");
  const { user } = useSession();
  const { tasks, days } = useJourney();
  const { open, question, seq, close } = useVigaPanel();
  const router = useRouter();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [infoOpen, setInfoOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const answered = useRef(0);

  function reply(asked: string): void {
    const trimmed = asked.trim();
    if (!trimmed) return;
    const answer = askViga(trimmed, tasks, days, {
      notInJourney: t("reply.notInJourney"),
      allDone: t("reply.allDone"),
      nextStep: (title) => t("reply.nextStep", { title }),
      locked: (title, blocker) => t("reply.locked", { title, blocker }),
      dayPlan: (day, ready, total) => t("reply.dayPlan", { day, ready, total }),
      dayPlanEmpty: (day) => t("reply.dayPlanEmpty", { day }),
      openTask: (title) => t("action.openTask", { title }),
      openDay: (day) => t("action.openDay", { day }),
      sourceTask: (title) => t("source.task", { title }),
      sourceDay: (day) => t("source.day", { day }),
    });
    setTurns((current) => [...current, { id: Date.now() + Math.random(), question: trimmed, reply: answer }]);
    setDraft("");
  }

  // Nút "Hỏi Viga về việc này" ở trang chi tiết gửi sẵn câu hỏi qua kho trạng thái; `seq` để hỏi lại cùng câu vẫn chạy.
  useEffect(() => {
    if (!question || seq === answered.current) return;
    answered.current = seq;
    reply(question);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question, seq]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    reply(draft);
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
            aria-label={t("infoLabel")}
            className={styles.iconButton}
            onClick={() => setInfoOpen(true)}
            title={t("infoLabel")}
            type="button"
          >
            <Sparkles aria-hidden="true" size={15} />
          </button>
          <button aria-label={t("close")} className={styles.iconButton} onClick={close} type="button">
            <X aria-hidden="true" size={15} />
          </button>
        </header>

        <div className={styles.body}>
          <p className={styles.mockNote}>{t("mockNote")}</p>

          {turns.length === 0 ? (
            <div className={styles.intro}>
              <div className={styles.row}>
                <VigaAvatar sizePx={26} />
                <p className={styles.bot}>{t("hello", { name: givenName(user.display_name) })}</p>
              </div>
              <div className={styles.quickColumn}>
                {quick.map((key) => (
                  <button key={key} onClick={() => reply(t(`quick.${key}`))} type="button">
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
                <p className={styles.user}>{turn.question}</p>
                <div className={styles.row}>
                  <VigaAvatar sizePx={26} />
                  <div className={styles.bot}>
                    <span className={`${styles.type} ${styles[turn.reply.responseType]}`}>{t(`type.${turn.reply.responseType}`)}</span>
                    <p>{turn.reply.message}</p>

                    {turn.reply.blockingTasks.length > 0 ? (
                      <ul className={styles.blocks}>
                        {turn.reply.blockingTasks.map((item) => (
                          <li key={item.taskId}>
                            <span className={`${styles.dot} ${styles[`dot_${item.state}`]}`} />
                            <span>{item.title}</span>
                            <small>{tt(`state.${item.state}`)}</small>
                          </li>
                        ))}
                      </ul>
                    ) : null}

                    {turn.reply.actions.length > 0 ? (
                      <div className={styles.actions}>
                        {turn.reply.actions.map((action, index) => (
                          <button
                            key={index}
                            onClick={() =>
                              router.push(
                                action.type === "OPEN_TASK"
                                  ? `/me/tasks/${action.taskId}`
                                  : { pathname: "/me/tasks", query: { stage: action.stageId } },
                              )
                            }
                            type="button"
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>
                    ) : null}

                    {turn.reply.sources.length > 0 ? (
                      <p className={styles.sources}>
                        {t("sourcesLabel")} {turn.reply.sources.join(" · ")}
                      </p>
                    ) : null}
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
                <button key={key} onClick={() => reply(t(`quick.${key}`))} type="button">
                  {t(`quick.${key}`)}
                </button>
              ))}
            </div>
          ) : null}
          <form className={styles.form} onSubmit={onSubmit}>
            <input
              aria-label={t("inputLabel")}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={t("placeholder")}
              ref={inputRef}
              value={draft}
            />
            <button aria-label={t("send")} disabled={!draft.trim()} type="submit">
              <Send aria-hidden="true" size={15} />
            </button>
          </form>
        </div>
      </aside>

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
            <p className={styles.infoNote}>{t("mockNote")}</p>
          </div>
        </PortalModal>
      ) : null}
    </>
  );
}
