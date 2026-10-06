"use client";

import { ArrowRight, Check, Lock } from "lucide-react";
import { useTranslations } from "next-intl";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { groupStyle } from "@/components/roadmap/taskGroups";
import { useSession } from "@/features/auth/SessionProvider";
import { Link } from "@/i18n/navigation";

import { DonutChart } from "./DonutChart";
import shared from "./employee.module.scss";
import { useJourney } from "./JourneyProvider";
import { JourneyProblemNotice } from "./JourneyProblemNotice";
import { PendingChangesBanner } from "./PendingChangesBanner";
import { stateOf } from "./journeyModel";
import styles from "./OverviewPage.module.scss";
import { PageHero } from "./PageHero";

const SHORTCUTS: { key: "tasks" | "documents" | "progress" | "profile"; href: string; icon: FlatIconName; tone: FlatTone }[] = [
  { key: "tasks", href: "/me/tasks", icon: "tasks", tone: "blue" },
  { key: "documents", href: "/me/documents", icon: "book", tone: "indigo" },
  { key: "progress", href: "/me/progress", icon: "route", tone: "teal" },
  { key: "profile", href: "/me/profile", icon: "user", tone: "slate" },
];

/** Trang đầu của nhân viên: lời chào, tiến độ, việc cần làm tiếp theo, việc vừa xong và lối tắt sang các trang khác. */
export function EmployeeOverviewPage() {
  const t = useTranslations("employee.overview");
  const tt = useTranslations("employee.task");
  const { user } = useSession();
  const { days, tasks, progress, loading } = useJourney();
  const nextTasks = tasks.filter((task) => stateOf(task) === "ready").slice(0, 4);
  const recentDone = tasks
    .filter((task) => stateOf(task) === "done")
    .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""))
    .slice(0, 4);
  const currentDay = days.find((day) => day.done < day.total) ?? days[days.length - 1] ?? null;

  const kpis: { key: "done" | "ready" | "locked" | "required"; icon: FlatIconName; tone: FlatTone; value: number; hint: string }[] = [
    { key: "done", icon: "check", tone: "green", value: progress.done, hint: t("kpi.doneHint", { total: progress.total }) },
    { key: "ready", icon: "tasks", tone: "blue", value: progress.ready, hint: t("kpi.readyHint") },
    { key: "locked", icon: "clock", tone: "slate", value: progress.locked, hint: t("kpi.lockedHint") },
    {
      key: "required",
      icon: "flag",
      tone: "amber",
      value: progress.requiredDone,
      hint: t("kpi.requiredHint", { total: progress.requiredTotal }),
    },
  ];

  return (
    <>
      <PageHero
        aside={
          <div className={styles.heroCard}>
            <span className={styles.heroLabel}>{t("heroProgressLabel")}</span>
            <b>{progress.pct}%</b>
            <div className={shared.meter}>
              <i style={{ width: `${progress.pct}%` }} />
            </div>
            <span className={styles.heroHint}>{t("heroProgressHint", { done: progress.done, total: progress.total })}</span>
            <Link className={styles.heroLink} href="/me/tasks">
              {t("openRoadmap")} <ArrowRight aria-hidden="true" size={14} />
            </Link>
          </div>
        }
        subtitle={t("subtitle")}
        avatarName={user.display_name}
        title={t("greeting", { name: user.display_name })}
      />

      <div className={shared.container}>
        <JourneyProblemNotice />
        <PendingChangesBanner />

        <div className={styles.kpis}>
          {kpis.map((kpi, i) => (
            <div className={`${shared.card} ${shared.hoverable} ${shared.rise} ${styles.kpi}`} key={kpi.key} style={{ "--i": i } as never}>
              <FlatIcon name={kpi.icon} size={30} tone={kpi.tone} />
              <div>
                <dt>{t(`kpi.${kpi.key}`)}</dt>
                <dd>{loading ? "—" : kpi.value}</dd>
                <small>{kpi.hint}</small>
              </div>
            </div>
          ))}
        </div>

        <div className={styles.columns}>
          <div className={styles.leftColumn}>
          <section className={`${shared.card} ${shared.rise} ${styles.grow}`} style={{ "--i": 4 } as never}>
            <div className={shared.cardHead}>
              <div>
                <h2>{t("next.title")}</h2>
                <small>{t("next.hint")}</small>
              </div>
              <Link className={shared.btnGhost} href="/me/tasks">
                {t("next.all")}
              </Link>
            </div>

            {loading ? (
              <div className={styles.list}>
                {[0, 1, 2].map((i) => (
                  <div className={shared.skeleton} key={i} style={{ height: 66, margin: "0 16px 10px" }} />
                ))}
              </div>
            ) : nextTasks.length === 0 ? (
              <div className={shared.empty}>
                <FlatIcon name="award" size={36} tone="violet" />
                <b>{t("next.emptyTitle")}</b>
                <span>{t("next.emptyBody")}</span>
              </div>
            ) : (
              <ul className={styles.list}>
                {nextTasks.map((task) => {
                  const group = groupStyle(task.task_group);
                  return (
                    <li key={task.id}>
                      <Link className={styles.row} href={`/me/tasks/${task.id}`} title={task.title}>
                        <span className={styles.rowIcon} style={{ background: `color-mix(in srgb, ${group.color} 12%, transparent)` }}>
                          <FlatIcon name={group.flat} size={22} tone={group.tone} />
                        </span>
                        <span className={styles.rowText}>
                          <b>{task.title}</b>
                          <small>
                            {task.stage_title} · {task.required ? tt("required") : tt("optional")}
                          </small>
                        </span>
                        <span className={styles.rowGo}>
                          <ArrowRight aria-hidden="true" size={15} />
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

            <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 6 } as never}>
              <div className={shared.cardHead}>
                <h2>{t("shortcuts.title")}</h2>
              </div>
              <div className={styles.shortcuts}>
                {SHORTCUTS.map((item) => (
                  <Link className={styles.shortcut} href={item.href} key={item.key}>
                    <FlatIcon name={item.icon} size={26} tone={item.tone} />
                    <span>
                      <b>{t(`shortcuts.${item.key}`)}</b>
                      <small>{t(`shortcuts.${item.key}Hint`)}</small>
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          </div>

          <div className={styles.rightColumn}>
            <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 4 } as never}>
              <div className={shared.cardHead}>
                <div>
                  <h2>{t("chart.title")}</h2>
                  <small>{currentDay ? t("currentDay", { day: currentDay.title }) : t("chart.hint")}</small>
                </div>
              </div>
              <DonutChart
                centerLabel={t("chart.center")}
                centerValue={`${progress.pct}%`}
                slices={[
                  { key: "done", label: tt("state.done"), value: progress.done, color: "#2f9a6f" },
                  { key: "ready", label: tt("state.ready"), value: progress.ready, color: "#1b6fb8" },
                  { key: "locked", label: tt("state.locked"), value: progress.locked, color: "#8f9bb0" },
                ]}
              />
            </section>

            <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 5 } as never}>
              <div className={shared.cardHead}>
                <h2>{t("recent.title")}</h2>
              </div>
              {recentDone.length === 0 ? (
                <p className={styles.quiet}>{t("recent.empty")}</p>
              ) : (
                <ul className={styles.doneList}>
                  {recentDone.map((task) => (
                    <li key={task.id}>
                      <Check aria-hidden="true" size={14} />
                      <span>{task.title}</span>
                    </li>
                  ))}
                </ul>
              )}
              {progress.locked > 0 ? (
                <p className={styles.lockedNote}>
                  <Lock aria-hidden="true" size={13} /> {t("recent.locked", { count: progress.locked })}
                </p>
              ) : null}
            </section>

          </div>
        </div>
      </div>


    </>
  );
}
