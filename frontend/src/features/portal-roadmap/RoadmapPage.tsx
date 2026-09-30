"use client";

import { Check, Lock, Loader2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { useSession } from "@/features/auth/SessionProvider";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type { EmployeeJourneyResponseDTO, EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./RoadmapPage.module.scss";

type CSSVars = React.CSSProperties & { "--c"?: string };

// Trạng thái hiển thị trên roadmap — gộp 7 trạng thái backend về 5 màu như prototype v15 (viewTasks v8).
type NodeState = "done" | "ready" | "wait" | "lock" | "over";

const NODE_COLOR: Record<NodeState, string> = {
  done: "#22a878",
  ready: "#3d8fe8",
  wait: "#e8ac3f",
  lock: "#8f9bb0",
  over: "#ea5a5a",
};

function nodeState(status: EmployeeTaskResponseDTO["status"]): NodeState {
  switch (status) {
    case "DONE":
      return "done";
    case "READY":
    case "IN_PROGRESS":
      return "ready";
    case "WAITING_EXTERNAL":
      return "wait";
    case "BLOCKED":
      return "over";
    default:
      return "lock";
  }
}

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) return t(`errors.${error.code}`);
  return t("errors.unavailable");
}

const ROW_HEIGHT = 118;
const TOP_OFFSET = 70;

function buildPath(xs: number[]): string {
  if (xs.length === 0) return "";
  let d = `M ${xs[0] * 10} 0 L ${xs[0] * 10} ${TOP_OFFSET}`;
  for (let i = 1; i < xs.length; i++) {
    const y0 = TOP_OFFSET + (i - 1) * ROW_HEIGHT;
    const y1 = TOP_OFFSET + i * ROW_HEIGHT;
    const ym = (y0 + y1) / 2;
    d += ` C ${xs[i - 1] * 10} ${ym} ${xs[i] * 10} ${ym} ${xs[i] * 10} ${y1}`;
  }
  d += ` L ${xs[xs.length - 1] * 10} ${xs.length * ROW_HEIGHT + TOP_OFFSET}`;
  return d;
}

/** Lộ trình nhân viên — bố cục cong zigzag y chang prototype v15 (viewTasks), nối API `/me/journey` thật. */
export function RoadmapPage() {
  const t = useTranslations("portalRoadmap");
  const { user } = useSession();

  const [journey, setJourney] = useState<EmployeeJourneyResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<EmployeeTaskResponseDTO | null>(null);
  const [completing, setCompleting] = useState(false);

  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .getMyJourney()
      .then((result) => {
        if (!cancelled) {
          setJourney(result);
          setError(null);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorMessage(t, caught));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadToken]);

  async function handleComplete() {
    if (!selected) return;
    setCompleting(true);
    try {
      await portalHrApi.completeTask(selected.id);
      setSelected(null);
      setReloadToken((token) => token + 1);
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setCompleting(false);
    }
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <Loader2 aria-hidden="true" className={styles.spin} size={22} />
        <span>{t("loading")}</span>
      </div>
    );
  }

  if (error && !journey) {
    return <p className={styles.banner}>{error}</p>;
  }

  if (!journey) return null;

  const tasks = journey.tasks;
  const xs = tasks.map((_, i) => (i % 2 === 0 ? 24 : 76));
  const path = buildPath(xs);
  const height = tasks.length * ROW_HEIGHT + TOP_OFFSET;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <PersonAvatar name={user.display_name} sizePx={44} />
        <div>
          <h1>{journey.journey_title}</h1>
          <p>{t("greeting", { name: user.display_name })}</p>
        </div>
      </header>

      {error ? <p className={styles.banner}>{error}</p> : null}

      <div className={styles.roadmap} style={{ height: height + 30 }}>
        <svg aria-hidden="true" className={styles.pathSvg} preserveAspectRatio="none" viewBox={`0 0 1000 ${height}`}>
          <path className={styles.pathShadow} d={path} />
          <path className={styles.path} d={path} />
        </svg>

        {tasks.slice(1).map((_, i) => {
          const y = TOP_OFFSET + i * ROW_HEIGHT + ROW_HEIGHT / 2;
          const dotColor = ["#f2c14e", "#3fc1c9", "#ea5a5a", "#ffffff"][i % 4];
          return <i className={styles.dot} key={`dot-${i}`} style={{ top: y, background: dotColor }} />;
        })}

        {tasks.map((task, i) => {
          const state = nodeState(task.status);
          const color = NODE_COLOR[state];
          const y = TOP_OFFSET + i * ROW_HEIGHT;
          const left = xs[i] === 24;
          const label =
            task.status === "DONE"
              ? t("status.DONE")
              : task.status === "LOCKED"
                ? t("status.LOCKED")
                : t(`status.${state.toUpperCase()}` as `status.${string}`);

          return (
            <div key={task.id}>
              <button
                aria-label={task.title}
                className={styles.node}
                onClick={() => setSelected(task)}
                style={{ left: `${xs[i]}%`, top: y, "--c": color } as CSSVars}
                type="button"
              >
                <span className={styles.ring}>
                  <span className={styles.in}>{task.status === "DONE" ? <Check size={22} /> : i + 1}</span>
                </span>
              </button>
              <button
                className={`${styles.pill} ${left ? styles.pillLeft : styles.pillRight}`}
                onClick={() => setSelected(task)}
                style={
                  {
                    top: y,
                    "--c": color,
                    ...(left ? { left: `calc(${xs[i]}% + 58px)` } : { right: `calc(${100 - xs[i]}% + 58px)` }),
                  } as CSSVars
                }
                type="button"
              >
                <small>
                  {task.stage_title} · {t("taskOrdinal", { n: i + 1 })}
                </small>
                <b>{task.title}</b>
                <em>{label}</em>
              </button>
            </div>
          );
        })}
      </div>

      <div className={styles.legend}>
        {(["done", "ready", "wait", "lock", "over"] as const).map((key) => (
          <span key={key}>
            <i style={{ background: NODE_COLOR[key] }} />
            {t(`status.${key === "lock" ? "LOCKED" : key.toUpperCase()}` as `status.${string}`)}
          </span>
        ))}
      </div>

      {selected ? (
        <div className={styles.modalBackdrop} onClick={() => setSelected(null)}>
          <div className={styles.modal} onClick={(event) => event.stopPropagation()}>
            <button aria-label={t("close")} className={styles.modalClose} onClick={() => setSelected(null)} type="button">
              <X aria-hidden="true" size={18} />
            </button>
            <small>{selected.stage_title}</small>
            <h2>{selected.title}</h2>
            <p className={styles.modalBody}>{selected.body_markdown}</p>
            {selected.status === "LOCKED" ? (
              <p className={styles.lockedHint}>
                <Lock aria-hidden="true" size={14} /> {t("lockedHint")}
              </p>
            ) : selected.status === "DONE" ? (
              <p className={styles.doneHint}>
                <Check aria-hidden="true" size={14} /> {t("doneHint")}
              </p>
            ) : (
              <button className={styles.completeButton} disabled={completing} onClick={handleComplete} type="button">
                {completing ? t("completing") : t("markDone")}
              </button>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
