"use client";

import { ChevronLeft, Plus } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { useSession } from "@/features/auth/SessionProvider";
import { portalHrApi } from "@/features/portal-hr/api";
import type { TemplateNodeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { ADD_STAGE_EVENT, TASKS_CHANGED_EVENT } from "@/features/portal-hr/TaskManagementPage";
import { Link } from "@/i18n/navigation";

import styles from "./TasksSidebar.module.scss";

/** Menu "ngày" thay cho menu thường khi ở Quản lý task (cổng .tree-back + .hr14-side-* của v15). */
export function TasksSidebar() {
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

  const stages = (templates ?? []).flatMap((tpl) => tpl.stages.map((s) => ({ ...s, published: tpl.status === "PUBLISHED" })));
  const selectedId = stages.some((s) => s.id === selectedParam) ? selectedParam : stages[0]?.id;

  return (
    <>
      <Link className={styles.treeBack} href={isAdmin ? "/admin/template" : "/admin"}>
        <ChevronLeft aria-hidden="true" size={14} /> {isAdmin ? t("backToTemplate") : t("backToOverview")}
      </Link>
      <div className={styles.sideHead}>
        <b>{t("sideTitle")}</b>
        <small>{t("sideHint")}</small>
      </div>
      <nav className={styles.days}>
        {stages.map((stage, i) => {
          const publishedCount = stage.published ? stage.tasks.length : 0;
          const pct = stage.tasks.length > 0 ? Math.round((publishedCount / stage.tasks.length) * 100) : 0;
          return (
            <Link
              className={`${styles.day} ${i % 4 === 0 ? "" : styles[`day${i % 4}`]} ${stage.id === selectedId ? styles.on : ""}`}
              href={{ pathname: "/admin/tasks", query: { stage: stage.id } }}
              key={stage.id}
            >
              <span className={styles.num}>
                <span className={styles.numText}>{/(\d+)/.exec(stage.title)?.[1] ?? i + 1}</span>
              </span>
              <div>
                <b className={styles.dayTitle}>
                  <span>{stage.title}</span>
                  <u className={stage.published ? styles.pubTag : styles.draftTag}>
                    {stage.published ? t("tagPublished") : t("tagDraft")}
                  </u>
                </b>
                <small>{t("sideCount", { total: stage.tasks.length, published: publishedCount })}</small>
                <i>
                  <em style={{ width: `${pct}%` }} />
                </i>
              </div>
              <strong>{pct}%</strong>
            </Link>
          );
        })}
        <button className={styles.addDay} onClick={() => window.dispatchEvent(new Event(ADD_STAGE_EVENT))} type="button">
          <Plus aria-hidden="true" size={14} /> {t("sideAdd")}
        </button>
      </nav>
    </>
  );
}
