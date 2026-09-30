"use client";

import { Check, ChevronRight, Eye, Flag, LayoutList, ListChecks, Lock, Route } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { useToast } from "@/components/portal-modal/PortalModal";
import { JourneyRoad, type RoadItem } from "@/components/roadmap/JourneyRoad";
import { groupStyle, NO_GROUP, TASK_GROUPS } from "@/components/roadmap/taskGroups";
import type { EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { useRouter } from "@/i18n/navigation";

import { DayRail } from "./DayRail";
import shared from "./employee.module.scss";
import { useSession } from "@/features/auth/SessionProvider";

import { useJourney } from "./JourneyProvider";
import { stateOf } from "./journeyModel";
import { PageHero } from "./PageHero";
import styles from "./TasksPage.module.scss";

type ViewMode = "road" | "list";

/**
 * "Nhiệm vụ" của nhân viên (view `tasks` + `task` của prototype v15): chọn ngày ở cây dọc bên trái, xem việc của ngày đó
 * dưới dạng lộ trình (dùng chung roadmap với HR) hoặc danh sách; bấm một việc để mở chi tiết và tự xác nhận hoàn thành.
 */
export function EmployeeTasksPage() {
  const t = useTranslations("employee.tasks");
  const { user } = useSession();
  const tt = useTranslations("employee.task");
  const params = useSearchParams();
  const { days, tasks, progress, problem, loading, busyTaskId, complete } = useJourney();
  // `null` = chưa chọn tay, cứ theo địa chỉ và mặc định.
  const [pickedStageId, setPickedStageId] = useState<number | null>(null);
  const [mode, setMode] = useState<ViewMode>("road");
  const [toastNode, showToast] = useToast();
  const router = useRouter();

  const stageParam = Number(params.get("stage")) || null;
  const taskParam = Number(params.get("task")) || null;
  const openTask = (id: number) => router.push(`/me/tasks/${id}`);

  // Ngày đang xem: ưu tiên ngày người dùng vừa bấm, rồi tới `?task=`/`?stage=` (từ Viga hoặc thông báo),
  // cuối cùng là ngày còn việc chưa xong — nơi nhân viên đang đứng.
  const stageFromTask = taskParam ? (tasks.find((task) => task.id === taskParam)?.stage_id ?? null) : null;
  const wantedStageId = stageFromTask ?? stageParam;
  const defaultStageId =
    (wantedStageId && days.some((row) => row.stageId === wantedStageId) ? wantedStageId : null) ??
    (days.find((row) => row.done < row.total) ?? days[0])?.stageId ??
    null;
  const openStageId = pickedStageId ?? defaultStageId;

  const day = days.find((d) => d.stageId === openStageId) ?? days[0] ?? null;
  const dayTasks = useMemo(() => day?.tasks ?? [], [day]);

  const items: RoadItem[] = dayTasks.map((task) => ({
    id: task.id,
    title: task.title,
    group: task.task_group,
    state: stateOf(task),
    pill: tt(`state.${stateOf(task)}`),
    chips: [
      { icon: <ListChecks aria-hidden="true" size={10} />, label: task.required ? tt("required") : tt("optional") },
      { icon: <Lock aria-hidden="true" size={10} />, label: t("prereq", { count: task.prerequisites.length }) },
    ],
  }));

  async function onComplete(task: EmployeeTaskResponseDTO) {
    const ok = await complete(task.id);
    showToast(ok ? t("completed", { title: task.title }) : t("completeFailed"));
  }

  return (
    <>
      <PageHero
        aside={
          <div className={styles.heroProgress}>
            <b>{progress.pct}%</b>
            <span>{t("heroProgress", { done: progress.done, total: progress.total })}</span>
            <div className={shared.meter}>
              <i style={{ width: `${progress.pct}%` }} />
            </div>
          </div>
        }
        avatarName={user.display_name}
        subtitle={t("subtitle")}
        title={t("title")}
      />

      <div className={shared.container}>
        {problem ? <p className={shared.banner}>{t(`problem.${problem}`)}</p> : null}

        {loading ? (
          <div className={`${shared.card} ${styles.layout}`}>
            <div className={styles.sideSkeleton}>
              {[0, 1, 2].map((i) => (
                <div className={shared.skeleton} key={i} style={{ height: 56 }} />
              ))}
            </div>
            <div className={shared.skeleton} style={{ height: 420, margin: 16 }} />
          </div>
        ) : days.length === 0 ? (
          <div className={`${shared.card} ${shared.empty}`}>
            <FlatIcon name="route" size={38} tone="blue" />
            <b>{t("emptyTitle")}</b>
            <span>{t("emptyBody")}</span>
          </div>
        ) : (
          <div className={`${shared.card} ${shared.rise} ${styles.layout}`}>
            <DayRail activeStageId={openStageId} days={days} onPick={setPickedStageId} />

            <section className={styles.main}>
              <div className={styles.dayHead}>
                <div className={styles.dayTitle}>
                  <span className={styles.dayIcon}>
                    <FlatIcon name="route" size={26} tone="blue" />
                  </span>
                  <div>
                    <h2>{day?.title}</h2>
                    <small>{t("dayCount", { done: day?.done ?? 0, total: day?.total ?? 0 })}</small>
                  </div>
                </div>

                <div className={styles.dayRight}>
                  <dl className={styles.dayStats}>
                    <div>
                      <FlatIcon name="check" size={22} tone="green" />
                      <dt>{t("stat.done")}</dt>
                      <dd>{day?.done ?? 0}</dd>
                    </div>
                    <div>
                      <FlatIcon name="tasks" size={22} tone="blue" />
                      <dt>{t("stat.ready")}</dt>
                      <dd>{dayTasks.filter((task) => stateOf(task) === "ready").length}</dd>
                    </div>
                    <div>
                      <FlatIcon name="clock" size={22} tone="slate" />
                      <dt>{t("stat.locked")}</dt>
                      <dd>{dayTasks.filter((task) => stateOf(task) === "locked").length}</dd>
                    </div>
                  </dl>
                  <div className={styles.modes} role="group">
                    <button
                      aria-pressed={mode === "road"}
                      className={mode === "road" ? styles.modeOn : ""}
                      onClick={() => setMode("road")}
                      type="button"
                    >
                      <Route aria-hidden="true" size={14} /> {t("modeRoad")}
                    </button>
                    <button
                      aria-pressed={mode === "list"}
                      className={mode === "list" ? styles.modeOn : ""}
                      onClick={() => setMode("list")}
                      type="button"
                    >
                      <LayoutList aria-hidden="true" size={14} /> {t("modeList")}
                    </button>
                  </div>
                </div>
              </div>

              {dayTasks.length === 0 ? (
                <div className={shared.empty}>
                  <Flag aria-hidden="true" size={28} />
                  <b>{t("emptyDayTitle")}</b>
                  <span>{t("emptyDayBody")}</span>
                </div>
              ) : mode === "road" ? (
                <JourneyRoad
                  actionsFor={(item) => {
                    const task = dayTasks.find((row) => row.id === item.id);
                    return [
                      { icon: <Eye aria-hidden="true" size={12} />, title: tt("view"), onClick: () => openTask(item.id) },
                      {
                        icon: <Check aria-hidden="true" size={12} />,
                        title: tt("markDone"),
                        tone: "success" as const,
                        disabled: !task || stateOf(task) !== "ready" || busyTaskId === item.id,
                        onClick: () => task && void onComplete(task),
                      },
                    ];
                  }}
                  items={items}
                  labels={{ start: t("start"), finish: t("finish"), taskNo: (n) => t("taskNo", { n }) }}
                  onOpen={(item) => openTask(item.id)}
                />
              ) : (
                <ul className={styles.list}>
                  {dayTasks.map((task) => {
                    const state = stateOf(task);
                    const group = groupStyle(task.task_group);
                    const blockers = task.prerequisites.filter((item) => !item.done);
                    return (
                      <li key={task.id}>
                        <button className={`${styles.row} ${styles[`row_${state}`]}`} onClick={() => openTask(task.id)} type="button">
                          <span className={styles.rowIcon} style={{ background: `color-mix(in srgb, ${group.color} 12%, transparent)` }}>
                            {state === "locked" ? (
                              <Lock aria-hidden="true" color={group.color} size={18} />
                            ) : state === "done" ? (
                              <Check aria-hidden="true" color="#2f9a6f" size={18} />
                            ) : (
                              <FlatIcon name={group.flat} size={20} tone={group.tone} />
                            )}
                          </span>
                          <span className={styles.rowText}>
                            <b>{task.title}</b>
                            <small>
                              {tt(`group.${group.key ?? "NONE"}`)} · {task.required ? tt("required") : tt("optional")}
                            </small>
                            {blockers.length > 0 ? (
                              <span className={styles.rowHint}>
                                <Lock aria-hidden="true" size={11} /> {t("needFirst", { titles: blockers.map((b) => b.title).join(", ") })}
                              </span>
                            ) : null}
                          </span>
                          <span className={`${styles.pill} ${styles[`pill_${state}`]}`}>{tt(`state.${state}`)}</span>
                          <ChevronRight aria-hidden="true" className={styles.rowGo} size={16} />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}

              <div className={styles.legend}>
                <b>{t("legendTitle")}</b>
                {TASK_GROUPS.map((group) => (
                  <span key={group.key}>
                    <i style={{ background: group.color }} />
                    {tt(`group.${group.key}`)}
                  </span>
                ))}
                {dayTasks.some((task) => !task.task_group) ? (
                  <span>
                    <i style={{ background: NO_GROUP.color }} />
                    {tt("group.NONE")}
                  </span>
                ) : null}
              </div>
            </section>
          </div>
        )}
      </div>

      {toastNode}
    </>
  );
}
