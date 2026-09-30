"use client";

import { Check, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import type { CSSProperties } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { groupStyle } from "@/components/roadmap/taskGroups";
import type { EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./DayRail.module.scss";
import { stateOf } from "./journeyModel";

type CSSVars = CSSProperties & { "--node"?: string };

/**
 * Cột trái của trang chi tiết việc: các việc trong cùng ngày xếp dọc thành một lộ trình nhỏ, cùng màu và icon nhóm
 * với mốc trên roadmap — việc đang xem được tô đậm, việc đã xong có dấu tích, việc bị khóa có ổ khóa.
 */
export function TaskRail({
  dayTitle,
  tasks,
  activeTaskId,
  onPick,
}: {
  dayTitle: string;
  tasks: EmployeeTaskResponseDTO[];
  activeTaskId: number;
  onPick: (taskId: number) => void;
}) {
  const t = useTranslations("employee.taskPage");
  const tt = useTranslations("employee.task");
  const tasksT = useTranslations("employee.tasks");
  const done = tasks.filter((task) => stateOf(task) === "done").length;

  return (
    <aside className={styles.side}>
      <div className={styles.sideHead}>
        <b>{t("railTitle", { day: dayTitle })}</b>
        <small>{t("railHint", { done, total: tasks.length })}</small>
      </div>

      <div className={styles.timeline}>
        <div className={styles.tlEnd}>
          <span className={`${styles.tlNode} ${styles.tlStart}`}>
            <FlatIcon name="flag" size={16} tone="red" />
          </span>
          <b>{tasksT("start")}</b>
        </div>

        {tasks.map((task, index) => {
          const state = stateOf(task);
          const group = groupStyle(task.task_group);
          const active = task.id === activeTaskId;
          return (
            <button
              aria-current={active ? "page" : undefined}
              className={`${styles.tlItem} ${styles.taskItem} ${active ? styles.taskOn : ""} ${styles[`state_${state}`]}`}
              key={task.id}
              onClick={() => onPick(task.id)}
              style={{ "--node": group.color } as CSSVars}
              title={task.title}
              type="button"
            >
              <span className={styles.taskNode}>
                {state === "done" ? (
                  <Check aria-hidden="true" size={14} />
                ) : state === "locked" ? (
                  <Lock aria-hidden="true" size={13} />
                ) : (
                  <FlatIcon name={group.flat} size={16} tone={group.tone} />
                )}
                <i className={styles.taskNum}>{index + 1}</i>
              </span>
              <span className={styles.tlCard}>
                <span className={styles.taskTitle}>{task.title}</span>
                <span className={styles.taskState}>
                  <i />
                  {tt(`state.${state}`)}
                </span>
              </span>
            </button>
          );
        })}

        <div className={`${styles.tlEnd} ${styles.tlLast}`}>
          <span className={`${styles.tlNode} ${styles.tlFinish}`}>
            <FlatIcon name="award" size={16} tone="violet" />
          </span>
          <b>{tasksT("finish")}</b>
        </div>
      </div>
    </aside>
  );
}
