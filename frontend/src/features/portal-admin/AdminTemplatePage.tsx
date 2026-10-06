"use client";

import { Building2, Copy, GitBranch, ListChecks, Pencil } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { ConfirmModal, useToast } from "@/components/portal-modal/PortalModal";
import { portalAdminApi } from "@/features/portal-admin/api";
import type {
  AdminTeamResponseDTO,
  AdminTemplateOverviewResponseDTO,
} from "@/features/portal-admin/dto/responseDTO/admin.response";
import { Link } from "@/i18n/navigation";

import { adminErrorMessage, adminStyles as s, IconChip, Kpi, Pager, PageHead, paginate, Pill } from "./adminUi";

const PAGE_SIZE = 5;

/** "Lộ trình mẫu chung" (v15 `viewATemplate`): bản gốc của công ty + trạng thái lộ trình của từng phòng ban, sao mẫu cho phòng ban chưa có. */
export function AdminTemplatePage() {
  const t = useTranslations("portalAdmin");
  const [toastNode, showToast] = useToast();
  const [overview, setOverview] = useState<AdminTemplateOverviewResponseDTO | null>(null);
  const [teams, setTeams] = useState<AdminTeamResponseDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copying, setCopying] = useState<AdminTeamResponseDTO | null>(null);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(1);

  const reload = useCallback(() => {
    portalAdminApi
      .getTemplateOverview()
      .then(setOverview)
      .catch((caught: unknown) => setError(adminErrorMessage(t, caught)));
    portalAdminApi
      .listTeams()
      .then((result) => setTeams(result.filter((team) => team.is_active)))
      .catch((caught: unknown) => setError(adminErrorMessage(t, caught)));
  }, [t]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function confirmCopy(team: AdminTeamResponseDTO) {
    setBusy(true);
    try {
      await portalAdminApi.copyTemplate(team.id);
      showToast(t("teams.copiedDone"));
      reload();
    } catch (caught) {
      setError(adminErrorMessage(t, caught));
    } finally {
      setCopying(null);
      setBusy(false);
    }
  }

  const { rows, page: current } = paginate(teams ?? [], page, PAGE_SIZE);

  return (
    <div className={s.page}>
      <PageHead
        actions={
          <Link className={s.btn} href="/admin/tasks">
            <Pencil aria-hidden="true" size={14} /> {t("template.edit")}
          </Link>
        }
        description={t("template.description")}
        icon={GitBranch}
        title={t("template.title")}
        tone="Indigo"
      />

      {error ? <p className={s.banner}>{error}</p> : null}

      {overview ? (
        <div className={s.kpiGrid3}>
          <Kpi
            icon={GitBranch}
            label={t("template.kpi.shared")}
            sub={overview.shared_title ?? t("template.kpi.noShared")}
            tone="Indigo"
            value={overview.shared_version ? `v${overview.shared_version}` : "—"}
          />
          <Kpi
            icon={ListChecks}
            label={t("template.kpi.tasks")}
            sub={t("template.kpi.tasksSub")}
            tone="Blue"
            value={overview.shared_task_count}
          />
          <Kpi
            icon={Building2}
            label={t("template.kpi.teams")}
            sub={t("template.kpi.teamsSub", { total: overview.active_teams })}
            tone="Teal"
            value={overview.teams_using_copy}
          />
        </div>
      ) : null}

      <div className={s.card}>
        <div className={s.cardHead}>
          <IconChip icon={Building2} tone="Blue" />
          <h2>{t("template.byTeam")}</h2>
        </div>
        <div className={s.tableWrap} style={{ minHeight: PAGE_SIZE * 49 + 41 }}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("teams.table.team")}</th>
                <th>{t("teams.table.hr")}</th>
                <th>{t("teams.table.journey")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {teams === null ? (
                <tr>
                  <td className={s.emptyCell} colSpan={4}>
                    {t("common.loading")}
                  </td>
                </tr>
              ) : (
                rows.map((team) => (
                  <tr key={team.id}>
                    <td style={{ minWidth: 220 }}>
                      <b>{team.name}</b>
                    </td>
                    <td>{team.hr_names[0] ?? <span className={s.faint}>{t("teams.noHr")}</span>}</td>
                    <td>
                      {team.journey_title ? (
                        `${team.journey_title} · v${team.journey_version}`
                      ) : (
                        <span className={s.faint}>{t("teams.noJourney")}</span>
                      )}
                    </td>
                    <td>
                      {team.journey_title ? (
                        <Pill tone="ok">{t("template.usingCopy")}</Pill>
                      ) : (
                        <button
                          className={`${s.btn} ${s.btnSm}`}
                          disabled={!overview?.shared_template_id}
                          onClick={() => setCopying(team)}
                          title={overview?.shared_template_id ? undefined : t("template.kpi.noShared")}
                          type="button"
                        >
                          <Copy aria-hidden="true" size={13} /> {t("teams.copyConfirm")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <Pager
          label={t("common.count", { count: teams?.length ?? 0 })}
          onPage={setPage}
          page={current}
          pageSize={PAGE_SIZE}
          total={teams?.length ?? 0}
        />
      </div>

      {copying ? (
        <ConfirmModal
          body={t("teams.copyBody", { name: copying.name })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={Copy}
          confirmLabel={t("teams.copyConfirm")}
          icon={Copy}
          onCancel={() => setCopying(null)}
          onConfirm={() => confirmCopy(copying)}
          title={t("teams.copyTitle", { name: copying.name })}
          tone="indigo"
        />
      ) : null}

      {toastNode}
    </div>
  );
}
