"use client";

import { useTranslations } from "next-intl";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { groupStyle, NO_GROUP, TASK_GROUPS } from "@/components/roadmap/taskGroups";

import shared from "./employee.module.scss";
import { useSession } from "@/features/auth/SessionProvider";

import { useJourney } from "./JourneyProvider";
import { stateOf } from "./journeyModel";
import { PageHero } from "./PageHero";
import styles from "./ProgressPage.module.scss";

/** "Theo dõi" (view `progress` của v15): tiến độ tổng, tiến độ từng ngày, phân bố theo nhóm việc và hoạt động gần đây. */
export function EmployeeProgressPage() {
  const t = useTranslations("employee.progress");
  const { user } = useSession();
  const tt = useTranslations("employee.task");
  const { days, tasks, progress, loading, problem } = useJourney();

  const kpis: { key: "overall" | "required" | "ready" | "locked"; icon: FlatIconName; tone: FlatTone; value: string; hint: string }[] = [
    {
      key: "overall",
      icon: "dashboard",
      tone: "blue",
      value: `${progress.pct}%`,
      hint: t("kpi.overallHint", { done: progress.done, total: progress.total }),
    },
    {
      key: "required",
      icon: "flag",
      tone: "amber",
      value: `${progress.requiredDone}/${progress.requiredTotal}`,
      hint: t("kpi.requiredHint"),
    },
    { key: "ready", icon: "tasks", tone: "green", value: String(progress.ready), hint: t("kpi.readyHint") },
    { key: "locked", icon: "clock", tone: "slate", value: String(progress.locked), hint: t("kpi.lockedHint") },
  ];

  const groups = [...TASK_GROUPS, NO_GROUP].map((group) => {
    const rows = tasks.filter((task) => (task.task_group ?? null) === group.key);
    return {
      key: group.key ?? "NONE",
      color: group.color,
      total: rows.length,
      done: rows.filter((task) => stateOf(task) === "done").length,
    };
  });
  const groupMax = Math.max(1, ...groups.map((group) => group.total));

  const recent = tasks
    .filter((task) => task.completed_at)
    .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""))
    .slice(0, 6);

  return (
    <>
      <PageHero
        avatarName={user.display_name}
        compact
        subtitle={t("subtitle")}
        title={t("title")}
      />

      <div className={shared.container}>
        {problem ? <p className={shared.banner}>{t(`problem.${problem}`)}</p> : null}

        <div className={styles.kpis}>
          {kpis.map((kpi, i) => (
            <div className={`${shared.card} ${shared.hoverable} ${shared.rise} ${styles.kpi}`} key={kpi.key} style={{ "--i": i } as never}>
              <FlatIcon name={kpi.icon} size={28} tone={kpi.tone} />
              <div>
                <dt>{t(`kpi.${kpi.key}`)}</dt>
                <dd>{loading ? "—" : kpi.value}</dd>
                <small>{kpi.hint}</small>
              </div>
            </div>
          ))}
        </div>

        <div className={styles.columns}>
          <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 4 } as never}>
            <div className={shared.cardHead}>
              <div>
                <h2>{t("byDay.title")}</h2>
                <small>{t("byDay.hint")}</small>
              </div>
            </div>
            {days.length === 0 ? (
              <p className={styles.quiet}>{t("noData")}</p>
            ) : (
              <ul className={styles.dayList}>
                {days.map((day) => (
                  <li key={day.stageId}>
                    <span className={styles.dayName}>{day.title}</span>
                    <span className={shared.meter}>
                      <i style={{ width: `${day.pct}%` }} />
                    </span>
                    <span className={styles.dayCount}>
                      {day.done}/{day.total}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 5 } as never}>
            <div className={shared.cardHead}>
              <div>
                <h2>{t("byGroup.title")}</h2>
                <small>{t("byGroup.hint")}</small>
              </div>
            </div>
            {tasks.length === 0 ? (
              <p className={styles.quiet}>{t("noData")}</p>
            ) : (
              <div className={styles.bars}>
                {groups
                  .filter((group) => group.total > 0)
                  .map((group) => (
                    <div className={styles.bar} key={group.key}>
                      <span className={styles.barLabel}>{tt(`group.${group.key}`)}</span>
                      <span
                        className={styles.barTrack}
                        style={{ height: `${(group.total / groupMax) * 100}%`, background: `color-mix(in srgb, ${group.color} 10%, transparent)` }}
                      >
                        <i style={{ background: group.color, height: `${group.total ? (group.done / group.total) * 100 : 0}%` }} />
                      </span>
                      <span className={styles.barValue}>
                        {group.done}/{group.total}
                      </span>
                    </div>
                  ))}
              </div>
            )}
            <p className={styles.legendNote}>{t("byGroup.legend")}</p>
          </section>
        </div>

        <section className={`${shared.card} ${shared.rise} ${styles.recent}`} style={{ "--i": 6 } as never}>
          <div className={shared.cardHead}>
            <h2>{t("recent.title")}</h2>
          </div>
          {recent.length === 0 ? (
            <p className={styles.quiet}>{t("recent.empty")}</p>
          ) : (
            <ol className={styles.timeline}>
              {recent.map((task) => {
                const group = groupStyle(task.task_group);
                return (
                  <li key={task.id}>
                    <i style={{ background: group.color }} />
                    <div>
                      <b>{task.title}</b>
                      <small>
                        {task.stage_title}
                        {task.completed_at ? ` · ${new Date(task.completed_at).toLocaleString()}` : ""}
                      </small>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>
    </>
  );
}
