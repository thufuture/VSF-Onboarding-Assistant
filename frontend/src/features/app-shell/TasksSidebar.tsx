"use client";

import { ChevronLeft, Plus } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { useSession } from "@/features/auth/SessionProvider";
import { portalHrApi } from "@/features/portal-hr/api";
import type { TemplateNodeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { ADD_STAGE_EVENT, TASKS_CHANGED_EVENT } from "@/features/portal-hr/TaskManagementPage";
import { Link } from "@/i18n/navigation";

import styles from "./TasksSidebar.module.scss";

/** Menu "ngày" thay cho menu thường khi ở Quản lý task (cổng .tree-back + .hr14-side-* của v15). */
export function TasksSidebar({ toggle }: { toggle?: ReactNode }) {
  const t = useTranslations("portalTasks");
  const { user } = useSession();
  // ADMIN tới đây từ "Lộ trình mẫu chung" (sửa bản mẫu dùng chung) nên quay lại đúng trang đó.
  const isAdmin = user.role === "ADMIN";
  const params = useSearchParams();
  const selectedParam = Number(params.get("stage"));
  const [templates, setTemplates] = useState<TemplateNodeResponseDTO[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      portalHrApi
        .listMyTemplates()
        .then((result) => {
          if (!cancelled) setTemplates(result);
        })
        .catch(() => undefined);
    };
    load();
    window.addEventListener(TASKS_CHANGED_EVENT, load);
    return () => {
      cancelled = true;
      window.removeEventListener(TASKS_CHANGED_EVENT, load);
    };
  }, []);

  const stages = (templates ?? []).flatMap((tpl) => tpl.stages.map((s) => ({ ...s, published: s.versions.some((v) => v.status === "APPLIED") })));
  const selectedId = stages.some((s) => s.id === selectedParam) ? selectedParam : stages[0]?.id;

  return (
    <>
      <div className={styles.treeTop}>
        <Link className={styles.treeBack} href={isAdmin ? "/admin/template" : "/admin"}>
          <ChevronLeft aria-hidden="true" size={14} /> {isAdmin ? t("backToTemplate") : t("backToOverview")}
        </Link>
        {toggle}
      </div>
      <div className={styles.sideHead}>
        <b>{t("sideTitle")}</b>
        <small>{t("sideHint")}</small>
      </div>
      <nav aria-label={t("sideTitle")} className={styles.timeline}>
        <div className={styles.tlEnd}>
          <span className={`${styles.tlNode} ${styles.tlStart}`}>
            <FlatIcon name="flag" size={16} tone="red" />
          </span>
          <b>{t("start")}</b>
        </div>
        {stages.map((stage, i) => {
          const publishedCount = stage.published ? stage.tasks.length : 0;
          const pct = stage.tasks.length > 0 ? Math.round((publishedCount / stage.tasks.length) * 100) : 0;
          const active = stage.id === selectedId;
          return (
            <Link
              aria-current={active ? "step" : undefined}
              className={`${styles.tlItem} ${active ? styles.tlOn : ""} ${stage.published ? styles.tlLive : styles.tlDraft}`}
              href={{ pathname: "/admin/tasks", query: { stage: stage.id } }}
              key={stage.id}
            >
              <span className={styles.tlNode}>{/(\d+)/.exec(stage.title)?.[1] ?? i + 1}</span>
              <div className={styles.tlCard}>
              <div className={styles.tlBody}>
                <b>
                  <span>{stage.title}</span>
                  <u>{stage.published ? t("tagPublished") : t("tagDraft")}</u>
                  <strong>{pct}%</strong>
                </b>
                <div className={styles.tlBar}>
                  <i>
                    <em style={{ width: `${pct}%` }} />
                  </i>
                </div>
              </div>
              </div>
            </Link>
          );
        })}
        <div className={`${styles.tlEnd} ${styles.tlLast}`}>
          <span className={`${styles.tlNode} ${styles.tlFinish}`}>
            <FlatIcon name="award" size={16} tone="violet" />
          </span>
          <b>{t("finish")}</b>
        </div>
        <button className={styles.addDay} onClick={() => window.dispatchEvent(new Event(ADD_STAGE_EVENT))} type="button">
          <Plus aria-hidden="true" size={14} /> {t("sideAdd")}
        </button>
      </nav>
    </>
  );
}
