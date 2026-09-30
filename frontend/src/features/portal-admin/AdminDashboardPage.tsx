"use client";

import { AlertTriangle, Building2, History, UserCheck, UserPlus, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { portalAdminApi } from "@/features/portal-admin/api";
import type { AdminDashboardResponseDTO } from "@/features/portal-admin/dto/responseDTO/admin.response";
import { useSession } from "@/features/auth/SessionProvider";
import { Link } from "@/i18n/navigation";

import { adminErrorMessage, adminStyles as s, formatDateTime, IconChip, Kpi } from "./adminUi";
import { auditIcon, auditTone } from "./auditMeta";

/** Tổng quan quản trị (v15 `viewADash`): KPI phòng ban/HR/nhân viên/cần xử lý, biểu đồ nhân viên theo phòng ban, hoạt động gần đây. */
export function AdminDashboardPage() {
  const t = useTranslations("portalAdmin");
  const { user } = useSession();
  const [data, setData] = useState<AdminDashboardResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    portalAdminApi
      .getDashboard()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(adminErrorMessage(t, caught));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const max = Math.max(1, ...(data?.employees_by_team.map(([, n]) => n) ?? [1]));

  return (
    <div className={s.page}>
      <header className={s.pagehead}>
        <PersonAvatar name={user.display_name} sizePx={48} />
        <div className={s.pageheadText}>
          <h1>{t("dashboard.title")}</h1>
          <p>{t("dashboard.description")}</p>
        </div>
        <div className={s.row}>
          <Link className={s.btnSec} href="/admin/users">
            <UserPlus aria-hidden="true" size={14} /> {t("users.add")}
          </Link>
          <Link className={s.btn} href="/admin/teams">
            <Building2 aria-hidden="true" size={14} /> {t("teams.add")}
          </Link>
        </div>
      </header>

      {error ? <p className={s.banner}>{error}</p> : null}

      {data ? (
        <>
          <div className={s.kpiGrid}>
            <Kpi
              icon={Building2}
              label={t("dashboard.kpi.teams")}
              sub={t("dashboard.kpi.teamsSub", { count: data.archived_teams })}
              tone="Blue"
              value={data.active_teams}
            />
            <Kpi
              icon={UserCheck}
              label={t("dashboard.kpi.hr")}
              sub={t("dashboard.kpi.hrSub")}
              tone="Indigo"
              value={data.hr_count}
            />
            <Kpi
              icon={Users}
              label={t("dashboard.kpi.employees")}
              sub={
                data.employees_without_team
                  ? t("dashboard.kpi.employeesNoTeam", { count: data.employees_without_team })
                  : t("dashboard.kpi.employeesAllInTeam")
              }
              tone="Teal"
              value={data.employee_count}
            />
            <Kpi
              icon={AlertTriangle}
              label={t("dashboard.kpi.attention")}
              sub={t("dashboard.kpi.attentionSub", {
                locked: data.inactive_users,
                noTeam: data.employees_without_team,
              })}
              tone="Rose"
              value={data.inactive_users + data.employees_without_team}
            />
          </div>

          <div className={s.grid2}>
            <div className={s.card}>
              <div className={s.cardHead}>
                <IconChip icon={Building2} tone="Blue" />
                <div>
                  <h2>{t("dashboard.byTeam")}</h2>
                  <small>{t("dashboard.byTeamSub")}</small>
                </div>
              </div>
              <div className={s.bars}>
                {data.employees_by_team.length === 0 ? <span className={s.faint}>{t("common.empty")}</span> : null}
                {data.employees_by_team.map(([name, count]) => (
                  <div className={s.bar} key={name}>
                    <span title={name}>{name}</span>
                    <div className={s.barTrack}>
                      <i style={{ width: `${(count / max) * 100}%` }} />
                    </div>
                    <b>{count}</b>
                  </div>
                ))}
              </div>
            </div>

            <div className={s.card}>
              <div className={s.cardHead}>
                <IconChip icon={History} tone="Slate" />
                <h2>{t("dashboard.recent")}</h2>
                <Link className={s.link} href="/admin/audit">
                  {t("dashboard.viewAudit")}
                </Link>
              </div>
              {data.recent_logs.length === 0 ? <div className={s.emptyCell}>{t("audit.empty")}</div> : null}
              {data.recent_logs.map((log) => {
                const Icon = auditIcon(log.action);
                return (
                  <div className={s.lrow} key={log.id}>
                    <IconChip icon={Icon} tone={auditTone(log.action)} />
                    <span className={s.lrowBody}>
                      <span>
                        <b>{t.has(`audit.actions.${log.action}`) ? t(`audit.actions.${log.action}`) : log.action}</b>
                        {log.target ? ` · ${log.target}` : ""}
                      </span>
                      <span className={s.faint}>
                        {log.actor_name ?? "—"} · {formatDateTime(log.created_at)}
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
