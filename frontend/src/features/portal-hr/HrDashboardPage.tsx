"use client";

import { Sparkles, UploadCloud } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { useSession } from "@/features/auth/SessionProvider";
import { AnalyticsPanel } from "@/features/portal-analytics/AnalyticsPanel";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type { HrDashboardResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { Link } from "@/i18n/navigation";

import styles from "./HrDashboardPage.module.scss";

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) return t(`errors.${error.code}`);
  return t("errors.unavailable");
}

/** Tổng quan HR thật — bố cục `.pagehead.hero` + `.kpi` của prototype v15 với số thật từ GET /portal/dashboard, cộng phần
 * số liệu theo thời gian (đường, cột, tròn, chi phí và độ trễ AI) từ GET /portal/analytics trong phạm vi phòng ban của HR. */
export function HrDashboardPage() {
  const t = useTranslations("hrDashboard");
  const { user } = useSession();
  const [data, setData] = useState<HrDashboardResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .getDashboard()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(errorMessage(t, caught));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.pageheadHero}>
        <PersonAvatar name={user.display_name} sizePx={48} />
        <div className={styles.pageheadText}>
          <h1>{t("greeting", { name: user.display_name })}</h1>
          <p>{data && data.journey_template_count > 0 ? t("journeyHint") : t("description")}</p>
        </div>
        <div className={styles.row}>
          <Link className={`${styles.btn} ${styles.btnSec}`} href="/admin/documents">
            <UploadCloud aria-hidden="true" size={14} /> {t("actions.documents.title")}
          </Link>
          <Link className={styles.btn} href="/admin/ai-tasks">
            <Sparkles aria-hidden="true" size={14} /> {t("actions.aiTasks.title")}
          </Link>
        </div>
      </header>

      {error ? <p className={styles.banner}>{error}</p> : null}

      {data ? (
        <div className={styles.kpiGrid}>
          <div className={`${styles.kpi} ${styles.toneBlue}`}>
            <div className={styles.kh}>
              <small>{t("kpi.tasks")}</small>
              <span className={styles.ichip}>
                <FlatIcon name="tasks" size={22} tone="indigo" />
              </span>
            </div>
            <b>{data.task_template_count}</b>
            <span className={styles.s}>{t("kpi.tasksSub")}</span>
          </div>
          <div className={`${styles.kpi} ${styles.toneIndigo}`}>
            <div className={styles.kh}>
              <small>{t("kpi.documents")}</small>
              <span className={styles.ichip}>
                <FlatIcon name="book" size={22} tone="green" />
              </span>
            </div>
            <b>{data.document_count}</b>
            <span className={styles.s}>{t("kpi.documentsSub")}</span>
          </div>
          <div className={`${styles.kpi} ${styles.toneTeal}`}>
            <div className={styles.kh}>
              <small>{t("kpi.templates")}</small>
              <span className={styles.ichip}>
                <FlatIcon name="route" size={22} tone="teal" />
              </span>
            </div>
            <b>{data.journey_template_count}</b>
            <span className={styles.s}>{t("kpi.templatesSub")}</span>
          </div>
          <div className={`${styles.kpi} ${styles.toneAmber}`}>
            <div className={styles.kh}>
              <small>{t("kpi.stages")}</small>
              <span className={styles.ichip}>
                <FlatIcon name="award" size={22} tone="amber" />
              </span>
            </div>
            <b>{data.journey_stage_count}</b>
            <span className={styles.s}>{t("kpi.stagesSub")}</span>
          </div>
        </div>
      ) : null}

      <AnalyticsPanel />
    </div>
  );
}
