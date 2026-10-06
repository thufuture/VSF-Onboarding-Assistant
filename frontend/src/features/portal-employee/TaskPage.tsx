"use client";

import { ArrowLeft, Check, ChevronRight, Loader2, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { VigaAvatar } from "@/components/avatar/VigaAvatar";
import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { useToast } from "@/components/portal-modal/PortalModal";
import { groupStyle } from "@/components/roadmap/taskGroups";
import { TaskSources } from "@/components/task-sources/TaskSources";
import { parseTaskBody } from "@/features/portal-hr/taskBody";
import { vigaApi } from "@/features/viga/api";
import { Link, useRouter } from "@/i18n/navigation";

import { ChangeCard } from "./ChangeCard";
import { TaskRail } from "./TaskRail";
import shared from "./employee.module.scss";
import { useSession } from "@/features/auth/SessionProvider";

import { useJourney } from "./JourneyProvider";
import { stateOf } from "./journeyModel";
import { PageHero } from "./PageHero";
import styles from "./TaskPage.module.scss";
import { useVigaPanel } from "./vigaPanelStore";

const TRACK = ["locked", "ready", "done"] as const;

/**
 * Trang chi tiết một việc (view `task` của prototype v15, dựng theo bảng màu portal): banner như các trang khác,
 * cây ngày bên trái giống trang Nhiệm vụ, hướng dẫn từng bước ở giữa; cột phải là chặng trạng thái, nút tự xác nhận
 * hoàn thành, nút hỏi Viga, việc tiên quyết và việc sẽ mở sau việc này.
 */
export function EmployeeTaskPage({ taskId }: { taskId: number }) {
  const t = useTranslations("employee.taskPage");
  const { user } = useSession();
  const tt = useTranslations("employee.task");
  const tc = useTranslations("employee.changes");
  const { tasks, days, loading, busyTaskId, complete, changedTaskIds, changeById, busyChangeId, previewChange, acceptChange, dismissChange } =
    useJourney();
  const { ask } = useVigaPanel();
  const router = useRouter();
  const [toastNode, showToast] = useToast();
  const [justDone, setJustDone] = useState(false);

  const task = tasks.find((row) => row.id === taskId) ?? null;

  // Ghi "việc vừa mở" để Viga hiểu "việc này" mà không cần giao diện gửi mã việc kèm câu hỏi (mục 15.3e).
  const openedId = task?.id ?? null;
  useEffect(() => {
    if (openedId !== null) void vigaApi.markTaskOpened(openedId);
  }, [openedId]);
  const group = groupStyle(task?.task_group ?? null);
  const state = task ? stateOf(task) : "locked";

  async function onComplete() {
    if (!task) return;
    const ok = await complete(task.id);
    if (ok) {
      setJustDone(true);
      showToast(t("completed", { title: task.title }));
    } else {
      showToast(t("completeFailed"));
    }
  }

  if (loading) {
    return (
      <div className={shared.container}>
        <div className={shared.skeleton} style={{ height: 120, marginBottom: 12 }} />
        <div className={shared.skeleton} style={{ height: 420 }} />
      </div>
    );
  }

  if (!task) {
    return (
      <>
        <PageHero
        avatarName={user.display_name}
        compact
        subtitle={t("notFoundBody")}
        title={t("notFoundTitle")}
      />
        <div className={shared.container}>
          <div className={`${shared.card} ${shared.empty}`}>
            <FlatIcon name="alert" size={36} tone="rose" />
            <b>{t("notFoundTitle")}</b>
            <span>{t("notFoundBody")}</span>
            <Link className={shared.btnGhost} href="/me/tasks">
              {t("backToTasks")}
            </Link>
          </div>
        </div>
      </>
    );
  }

  const dayTasks = days.find((day) => day.stageId === task.stage_id)?.tasks ?? [task];
  const parts = parseTaskBody(task.body_markdown);
  const structured = parts.why || parts.done || parts.steps.length > 0;
  const pendingChange = changeById.get(task.pending_change_id ?? changedTaskIds.get(task.id) ?? -1)?.change ?? null;
  const blockers = task.prerequisites.filter((item) => !item.done);
  const prereqTasks = tasks.filter((row) => task.prerequisites.some((item) => item.title === row.title));
  const unlocks = tasks.filter((row) => row.prerequisites.some((item) => item.title === task.title));

  return (
    <>
      <PageHero
        aside={
          <div className={styles.heroCard}>
            <span className={`${styles.pill} ${styles[`pill_${state}`]}`}>{tt(`state.${state}`)}</span>
            {pendingChange ? <span className={`${styles.pill} ${styles.pill_changed}`}>{tc("changed")}</span> : null}
            <span className={styles.heroGroup}>
              <FlatIcon name={group.flat} size={20} tone={group.tone} />
              {tt(`group.${group.key ?? "NONE"}`)}
            </span>
          </div>
        }
        compact
        subtitle={t("heroSubtitle", {
          group: tt(`group.${group.key ?? "NONE"}`),
          required: task.required ? tt("required") : tt("optional"),
          day: task.stage_title,
        })}
        title={task.title}
      />

      <div className={shared.container}>
        <nav aria-label={t("breadcrumb")} className={styles.crumb}>
          <Link href="/me/tasks">
            <ArrowLeft aria-hidden="true" size={13} /> {t("allTasks")}
          </Link>
          <ChevronRight aria-hidden="true" size={12} />
          <Link href={{ pathname: "/me/tasks", query: { stage: task.stage_id } }}>{task.stage_title}</Link>
        </nav>

        <div className={`${shared.card} ${shared.rise} ${styles.layout}`}>
          <TaskRail
            activeTaskId={task.id}
            dayTitle={task.stage_title}
            onPick={(id) => router.push(`/me/tasks/${id}`)}
            tasks={dayTasks}
          />

          <div className={styles.cols}>
            <div className={styles.left}>
              {pendingChange ? (
                <ChangeCard
                  busy={busyChangeId === pendingChange.id}
                  change={pendingChange}
                  compact
                  onAccept={(id) => void acceptChange(id)}
                  onDismiss={(id) => void dismissChange(id)}
                  previewChange={previewChange}
                />
              ) : null}

              {blockers.length > 0 ? (
                <div className={styles.lockNote}>
                  <Lock aria-hidden="true" size={16} />
                  <div>
                    <b>{t("lockedTitle")}</b>
                    <p>{t("lockedBody")}</p>
                  </div>
                </div>
              ) : null}

              {parts.why ? (
                <section className={styles.block}>
                  <div className={styles.blockHead}>
                    <FlatIcon name="lifebuoy" size={22} tone="blue" />
                    <h2>{t("why")}</h2>
                  </div>
                  <p className={styles.prose}>{parts.why}</p>
                </section>
              ) : null}

              {parts.steps.length > 0 ? (
                <section className={styles.block}>
                  <div className={styles.blockHead}>
                    <FlatIcon name="tasks" size={22} tone="indigo" />
                    <div>
                      <h2>{t("steps")}</h2>
                      <small>{t("stepsHint")}</small>
                    </div>
                  </div>
                  <ol className={styles.steps}>
                    {parts.steps.map((step, index) => (
                      <li key={index}>
                        <span className={styles.stepNum}>{index + 1}</span>
                        <p>{step}</p>
                      </li>
                    ))}
                  </ol>
                </section>
              ) : null}

              {parts.done ? (
                <section className={styles.block}>
                  <div className={styles.blockHead}>
                    <FlatIcon name="check" size={22} tone="green" />
                    <h2>{t("doneWhen")}</h2>
                  </div>
                  <p className={styles.prose}>{parts.done}</p>
                </section>
              ) : null}

              {!structured ? (
                <section className={styles.block}>
                  <div className={styles.blockHead}>
                    <FlatIcon name="file" size={22} tone="blue" />
                    <h2>{t("guide")}</h2>
                  </div>
                  <div className={styles.markdown}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{task.body_markdown || t("noBody")}</ReactMarkdown>
                  </div>
                </section>
              ) : null}
            </div>

            <aside className={styles.rail}>
              <section className={styles.railCard}>
                <div className={styles.railHead}>
                  <h2>{t("statusTitle")}</h2>
                </div>
                <div className={styles.railBody}>
                  <ol className={styles.track}>
                    {TRACK.map((step) => {
                      const reached = TRACK.indexOf(step) <= TRACK.indexOf(state);
                      return (
                        <li className={`${reached ? styles.trackOn : ""} ${step === state ? styles.trackNow : ""}`} key={step}>
                          <i />
                          <span>{tt(`state.${step}`)}</span>
                        </li>
                      );
                    })}
                  </ol>

                  {state === "done" ? (
                    <p className={styles.doneNote}>
                      <Check aria-hidden="true" size={15} />
                      {task.completed_at ? t("doneAt", { at: new Date(task.completed_at).toLocaleString() }) : tt("alreadyDone")}
                    </p>
                  ) : state === "locked" ? (
                    <p className={styles.lockedHint}>{t("lockedHint")}</p>
                  ) : (
                    <p className={styles.readyHint}>{t("readyHint")}</p>
                  )}

                  <button
                    className={`${shared.btn} ${shared.btnSuccess} ${styles.doneButton}`}
                    disabled={state !== "ready" || busyTaskId === task.id}
                    onClick={() => void onComplete()}
                    type="button"
                  >
                    {busyTaskId === task.id ? (
                      <Loader2 aria-hidden="true" className={styles.spin} size={15} />
                    ) : (
                      <Check aria-hidden="true" size={15} />
                    )}{" "}
                    {tt("markDone")}
                  </button>

                  {justDone && unlocks.length > 0 ? (
                    <p className={styles.unlockedNote}>{t("unlockedAfter", { count: unlocks.length })}</p>
                  ) : null}
                </div>
              </section>

              <button className={styles.vigaButton} onClick={() => ask(t("askVigaQuestion", { title: task.title }))} type="button">
                <VigaAvatar sizePx={26} />
                <span>{t("askViga")}</span>
              </button>

              {task.sources && task.sources.length > 0 ? (
                <section className={styles.railCard}>
                  <div className={styles.railHead}>
                    <h2>{t("sourcesTitle")}</h2>
                    <small>{t("sourcesHint")}</small>
                  </div>
                  <div className={styles.railBody}>
                    <TaskSources sources={task.sources} />
                  </div>
                </section>
              ) : null}

              {prereqTasks.length > 0 ? (
                <section className={styles.railCard}>
                  <div className={styles.railHead}>
                    <h2>{t("prereqTitle")}</h2>
                  </div>
                  <ul className={styles.links}>
                    {prereqTasks.map((row) => (
                      <li key={row.id}>
                        <button onClick={() => router.push(`/me/tasks/${row.id}`)} title={row.title} type="button">
                          <span className={`${styles.dot} ${styles[`dot_${stateOf(row)}`]}`} />
                          <span className={styles.linkText}>
                            <b>{row.title}</b>
                            <small>{tt(`state.${stateOf(row)}`)}</small>
                          </span>
                          <ChevronRight aria-hidden="true" size={14} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {unlocks.length > 0 ? (
                <section className={styles.railCard}>
                  <div className={styles.railHead}>
                    <h2>{t("unlocksTitle")}</h2>
                    <small>{t("unlocksHint")}</small>
                  </div>
                  <ul className={styles.links}>
                    {unlocks.map((row) => (
                      <li key={row.id}>
                        <button onClick={() => router.push(`/me/tasks/${row.id}`)} title={row.title} type="button">
                          <span className={`${styles.dot} ${styles[`dot_${stateOf(row)}`]}`} />
                          <span className={styles.linkText}>
                            <b>{row.title}</b>
                            <small>{tt(`state.${stateOf(row)}`)}</small>
                          </span>
                          <ChevronRight aria-hidden="true" size={14} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </aside>
          </div>
        </div>
      </div>
      {toastNode}
    </>
  );
}
