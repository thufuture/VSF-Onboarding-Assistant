"use client";

import { Archive, ArchiveRestore, Building2, Check, Copy, Eye, Pencil, Plus, Search, Trash2, UserPlus } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { portalAdminApi } from "@/features/portal-admin/api";
import type {
  AdminMembershipResponseDTO,
  AdminTeamResponseDTO,
  AdminUserResponseDTO,
} from "@/features/portal-admin/dto/responseDTO/admin.response";

import { adminErrorMessage, adminStyles as s, formatDate, IconChip, Kpi, Pager, PageHead, paginate, Pill } from "./adminUi";
import { UserCheck, Users, GitBranch } from "lucide-react";

const PAGE_SIZE = 6;
type StatusFilter = "all" | "ACTIVE" | "ARCHIVED";
type Modal =
  | { kind: "edit"; team: AdminTeamResponseDTO | null }
  | { kind: "detail"; teamId: number }
  | { kind: "archive"; team: AdminTeamResponseDTO }
  | { kind: "copy"; team: AdminTeamResponseDTO }
  | { kind: "addMember"; teamId: number }
  | { kind: "removeMember"; member: AdminMembershipResponseDTO };

/** "Phòng ban" (v15 `viewADepts`): tạo/sửa, HR phụ trách, chi tiết + thành viên, lưu trữ/khôi phục, sao lộ trình mẫu chung. */
export function AdminTeamsPage() {
  const t = useTranslations("portalAdmin");
  const [toastNode, showToast] = useToast();

  const [teams, setTeams] = useState<AdminTeamResponseDTO[] | null>(null);
  const [users, setUsers] = useState<AdminUserResponseDTO[]>([]);
  const [members, setMembers] = useState<AdminMembershipResponseDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal | null>(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [hrId, setHrId] = useState("");
  const [copyShared, setCopyShared] = useState(true);
  const [memberUserId, setMemberUserId] = useState("");

  const reload = useCallback(() => {
    portalAdminApi
      .listTeams()
      .then(setTeams)
      .catch((caught: unknown) => setError(adminErrorMessage(t, caught)));
    portalAdminApi.listMemberships().then(setMembers).catch(() => undefined);
    portalAdminApi.listUsers().then(setUsers).catch(() => undefined);
  }, [t]);

  useEffect(() => {
    reload();
  }, [reload]);

  const hrUsers = useMemo(() => users.filter((u) => u.role === "HR" && u.status === "ACTIVE"), [users]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (teams ?? []).filter(
      (team) =>
        (status === "all" || (status === "ACTIVE") === team.is_active) &&
        (!q || team.name.toLowerCase().includes(q) || team.code.toLowerCase().includes(q)),
    );
  }, [teams, query, status]);
  const { rows, page: current } = paginate(filtered, page, PAGE_SIZE);

  function openEdit(team: AdminTeamResponseDTO | null) {
    setFormError(null);
    setName(team?.name ?? "");
    setCode(team?.code ?? "");
    setHrId(team?.hr_user_ids[0] ? String(team.hr_user_ids[0]) : "");
    setCopyShared(true);
    setModal({ kind: "edit", team });
  }

  async function run(action: () => Promise<unknown>, done: string, closeTo: Modal | null = null) {
    setBusy(true);
    try {
      await action();
      setModal(closeTo);
      showToast(done);
      reload();
    } catch (caught) {
      setModal(closeTo);
      setError(adminErrorMessage(t, caught));
    } finally {
      setBusy(false);
    }
  }

  async function submitTeam(event: FormEvent) {
    event.preventDefault();
    if (modal?.kind !== "edit") return;
    setBusy(true);
    setFormError(null);
    try {
      if (modal.team) {
        await portalAdminApi.updateTeam(modal.team.id, { name, hr_user_id: hrId ? Number(hrId) : null });
        showToast(t("teams.saved"));
      } else {
        await portalAdminApi.createTeam({
          name,
          code,
          hr_user_id: hrId ? Number(hrId) : null,
          copy_shared_template: copyShared,
        });
        showToast(t("teams.created"));
      }
      setModal(null);
      reload();
    } catch (caught) {
      setFormError(adminErrorMessage(t, caught));
    } finally {
      setBusy(false);
    }
  }

  const detailTeam = modal?.kind === "detail" || modal?.kind === "addMember" ? teams?.find((x) => x.id === modal.teamId) : undefined;
  const detailMembers = detailTeam ? members.filter((x) => x.team_id === detailTeam.id) : [];
  const candidates = detailTeam
    ? users.filter((u) => u.role !== "ADMIN" && !detailMembers.some((x) => x.user_id === u.id))
    : [];

  return (
    <div className={s.page}>
      <PageHead
        actions={
          <button className={s.btn} onClick={() => openEdit(null)} type="button">
            <Plus aria-hidden="true" size={14} /> {t("teams.add")}
          </button>
        }
        description={t("teams.description")}
        icon={Building2}
        title={t("teams.title")}
        tone="Indigo"
      />

      {error ? <p className={s.banner}>{error}</p> : null}

      <div className={s.card}>
        <div className={s.tbar}>
          <div className={s.search}>
            <Search aria-hidden="true" size={14} />
            <input
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder={t("teams.search")}
              value={query}
            />
          </div>
          <div className={s.chips}>
            {(["all", "ACTIVE", "ARCHIVED"] as const).map((key) => (
              <button
                className={`${s.chip} ${status === key ? s.chipOn : ""}`}
                key={key}
                onClick={() => {
                  setStatus(key);
                  setPage(1);
                }}
                type="button"
              >
                {t(`teams.filter.${key}`)}
              </button>
            ))}
          </div>
        </div>
        <div className={s.tableWrap} style={{ minHeight: PAGE_SIZE * 62 + 41 }}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("teams.table.team")}</th>
                <th>{t("teams.table.status")}</th>
                <th>{t("teams.table.hr")}</th>
                <th>{t("teams.table.members")}</th>
                <th>{t("teams.table.journey")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {teams === null ? (
                <tr>
                  <td className={s.emptyCell} colSpan={6}>
                    {t("common.loading")}
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td className={s.emptyCell} colSpan={6}>
                    {t("teams.empty")}
                  </td>
                </tr>
              ) : (
                rows.map((team) => (
                  <tr key={team.id}>
                    <td style={{ minWidth: 230 }}>
                      <div className={s.cellrow}>
                        <IconChip icon={Building2} size={16} tone={team.is_active ? "Blue" : "Slate"} />
                        <div>
                          <b>{team.name}</b>
                          <div>
                            <span className={`${s.tag} ${s.mono}`}>{team.code}</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <Pill tone={team.is_active ? "ok" : "neutral"}>
                        {team.is_active ? t("teams.active") : t("teams.archived")}
                      </Pill>
                    </td>
                    <td>
                      {team.hr_names.length ? (
                        <div className={s.cellrow}>
                          <PersonAvatar name={team.hr_names[0]} sizePx={26} />
                          <span>
                            {team.hr_names[0]}
                            {team.hr_names.length > 1 ? ` +${team.hr_names.length - 1}` : ""}
                          </span>
                        </div>
                      ) : (
                        <span className={s.faint}>{t("teams.noHr")}</span>
                      )}
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {t("teams.memberCount", { employees: team.employee_count, hr: team.hr_count })}
                    </td>
                    <td style={{ minWidth: 200 }}>
                      {team.journey_title ? (
                        `${team.journey_title} · v${team.journey_version} (${t(`teams.journeyStatus.${team.journey_status}`)})`
                      ) : (
                        <span className={s.faint}>{t("teams.noJourney")}</span>
                      )}
                    </td>
                    <td>
                      <div className={s.rowActions}>
                        <button
                          className={s.iconBtn}
                          onClick={() => setModal({ kind: "detail", teamId: team.id })}
                          title={t("teams.detail")}
                          type="button"
                        >
                          <Eye aria-hidden="true" size={13} />
                        </button>
                        <button className={s.iconBtn} onClick={() => openEdit(team)} title={t("teams.edit")} type="button">
                          <Pencil aria-hidden="true" size={13} />
                        </button>
                        <button
                          className={`${s.iconBtn} ${team.is_active ? s.iconDanger : s.iconOk}`}
                          onClick={() => setModal({ kind: "archive", team })}
                          title={team.is_active ? t("teams.archive") : t("teams.restore")}
                          type="button"
                        >
                          {team.is_active ? (
                            <Archive aria-hidden="true" size={13} />
                          ) : (
                            <ArchiveRestore aria-hidden="true" size={13} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <Pager
          label={t("common.count", { count: filtered.length })}
          onPage={setPage}
          page={current}
          pageSize={PAGE_SIZE}
          total={filtered.length}
        />
      </div>

      {modal?.kind === "edit" ? (
        <PortalModal
          closeLabel={t("common.close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("common.cancel")}
              </button>
              <button className={m.btn} disabled={busy} form="admin-team-form" type="submit">
                <Check aria-hidden="true" size={14} /> {t("common.save")}
              </button>
            </>
          }
          icon={Building2}
          onClose={() => setModal(null)}
          title={modal.team ? t("teams.editTitle") : t("teams.add")}
          tone="indigo"
        >
          <form id="admin-team-form" onSubmit={submitTeam}>
            <div className={m.fgrid}>
              <div className={m.span2}>
                <label htmlFor="d-name">{t("teams.form.name")}</label>
                <input id="d-name" onChange={(e) => setName(e.target.value)} required type="text" value={name} />
              </div>
              <div>
                <label htmlFor="d-key">{t("teams.form.code")}</label>
                <input
                  disabled={modal.team !== null}
                  id="d-key"
                  onChange={(e) => setCode(e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))}
                  required
                  type="text"
                  value={code}
                />
              </div>
              <div>
                <label htmlFor="d-hr">{t("teams.form.hr")}</label>
                <select id="d-hr" onChange={(e) => setHrId(e.target.value)} value={hrId}>
                  <option value="">{t("teams.form.noHr")}</option>
                  {hrUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.display_name}
                    </option>
                  ))}
                </select>
              </div>
              {modal.team ? null : (
                <div className={m.span2}>
                  <label className={m.subitem}>
                    <input checked={copyShared} onChange={(e) => setCopyShared(e.target.checked)} type="checkbox" />
                    <span>{t("teams.form.copyShared")}</span>
                  </label>
                </div>
              )}
            </div>
            {formError ? <p className={s.banner}>{formError}</p> : null}
          </form>
        </PortalModal>
      ) : null}

      {modal?.kind === "archive" ? (
        <ConfirmModal
          body={t(modal.team.is_active ? "teams.archiveBody" : "teams.restoreBody", { name: modal.team.name })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={modal.team.is_active ? Archive : ArchiveRestore}
          confirmLabel={modal.team.is_active ? t("teams.archive") : t("teams.restore")}
          danger={modal.team.is_active}
          icon={modal.team.is_active ? Archive : ArchiveRestore}
          onCancel={() => setModal(null)}
          onConfirm={() =>
            run(
              () => portalAdminApi.setTeamStatus(modal.team.id, !modal.team.is_active),
              modal.team.is_active ? t("teams.archivedDone") : t("teams.restoredDone"),
            )
          }
          title={t(modal.team.is_active ? "teams.archiveTitle" : "teams.restoreTitle", { name: modal.team.name })}
          tone={modal.team.is_active ? "rose" : "teal"}
          warning={modal.team.is_active ? t("teams.archiveWarning") : undefined}
        />
      ) : null}

      {modal?.kind === "copy" ? (
        <ConfirmModal
          body={t("teams.copyBody", { name: modal.team.name })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={Copy}
          confirmLabel={t("teams.copyConfirm")}
          icon={Copy}
          onCancel={() => setModal({ kind: "detail", teamId: modal.team.id })}
          onConfirm={() =>
            run(
              () => portalAdminApi.copyTemplate(modal.team.id),
              t("teams.copiedDone"),
              { kind: "detail", teamId: modal.team.id },
            )
          }
          title={t("teams.copyTitle", { name: modal.team.name })}
          tone="indigo"
        />
      ) : null}

      {modal?.kind === "removeMember" ? (
        <ConfirmModal
          body={t("members.removeBody", { user: modal.member.user_name, team: modal.member.team_name })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={Trash2}
          confirmLabel={t("members.remove")}
          danger
          icon={Trash2}
          onCancel={() => setModal({ kind: "detail", teamId: modal.member.team_id })}
          onConfirm={() =>
            run(
              () => portalAdminApi.removeMembership(modal.member.team_id, modal.member.user_id),
              t("members.removedDone"),
              { kind: "detail", teamId: modal.member.team_id },
            )
          }
          title={t("members.removeTitle", { user: modal.member.user_name })}
        />
      ) : null}

      {(modal?.kind === "detail" || modal?.kind === "addMember") && detailTeam ? (
        <PortalModal
          closeLabel={t("common.close")}
          footer={
            modal.kind === "addMember" ? (
              <>
                <button className={m.btnSec} onClick={() => setModal({ kind: "detail", teamId: detailTeam.id })} type="button">
                  {t("common.cancel")}
                </button>
                <button
                  className={m.btn}
                  disabled={busy || !memberUserId}
                  onClick={() =>
                    run(
                      () => portalAdminApi.addMembership({ team_id: detailTeam.id, user_id: Number(memberUserId) }),
                      t("members.addedDone"),
                      { kind: "detail", teamId: detailTeam.id },
                    )
                  }
                  type="button"
                >
                  <Check aria-hidden="true" size={14} /> {t("members.assign")}
                </button>
              </>
            ) : (
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("common.close")}
              </button>
            )
          }
          icon={Building2}
          onClose={() => setModal(null)}
          subtitle={t("teams.detailSub", {
            code: detailTeam.code,
            date: formatDate(detailTeam.created_at),
            state: detailTeam.is_active ? t("teams.active") : t("teams.archived"),
          })}
          title={detailTeam.name}
          tone="indigo"
          wide
        >
          {modal.kind === "addMember" ? (
            <div className={m.fgrid}>
              <div className={m.span2}>
                <label htmlFor="m-user">{t("members.user")}</label>
                <select id="m-user" onChange={(e) => setMemberUserId(e.target.value)} value={memberUserId}>
                  <option value="">{t("members.pickUser")}</option>
                  {candidates.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.display_name} ({t(`roles.${u.role}`)})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <>
              <div className={s.kpiGrid3}>
                <Kpi
                  icon={UserCheck}
                  label={t("teams.table.hr")}
                  tone="Blue"
                  value={<span style={{ fontSize: 15 }}>{detailTeam.hr_names[0] ?? t("teams.noHr")}</span>}
                />
                <Kpi icon={Users} label={t("dashboard.kpi.employees")} tone="Teal" value={detailTeam.employee_count} />
                <Kpi
                  icon={GitBranch}
                  label={t("teams.table.journey")}
                  tone="Indigo"
                  value={
                    <span style={{ fontSize: 15 }}>
                      {detailTeam.journey_version ? `v${detailTeam.journey_version}` : t("teams.noJourney")}
                    </span>
                  }
                />
              </div>
              <div className={s.row} style={{ justifyContent: "space-between", margin: "14px 0 6px" }}>
                <b>{t("members.title")}</b>
                <div className={s.row}>
                  {detailTeam.journey_title ? null : (
                    <button
                      className={`${s.btnSec} ${s.btnSm}`}
                      onClick={() => setModal({ kind: "copy", team: detailTeam })}
                      type="button"
                    >
                      <Copy aria-hidden="true" size={13} /> {t("teams.copyConfirm")}
                    </button>
                  )}
                  <button
                    className={`${s.btn} ${s.btnSm}`}
                    onClick={() => {
                      setMemberUserId("");
                      setModal({ kind: "addMember", teamId: detailTeam.id });
                    }}
                    type="button"
                  >
                    <UserPlus aria-hidden="true" size={13} /> {t("members.add")}
                  </button>
                </div>
              </div>
              <div className={s.tableWrap}>
                <table className={s.table}>
                  <thead>
                    <tr>
                      <th>{t("users.table.user")}</th>
                      <th>{t("members.table.teamRole")}</th>
                      <th>{t("members.table.access")}</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {detailMembers.length === 0 ? (
                      <tr>
                        <td className={s.emptyCell} colSpan={4}>
                          {t("members.empty")}
                        </td>
                      </tr>
                    ) : (
                      detailMembers.map((member) => (
                        <tr key={member.user_id}>
                          <td>
                            <div className={s.cellrow}>
                              <PersonAvatar name={member.user_name} sizePx={30} />
                              <div>
                                <b>{member.user_name}</b>
                                <div className={s.faint}>{member.user_email}</div>
                              </div>
                            </div>
                          </td>
                          <td>{t(`members.teamRole.${member.team_role}`)}</td>
                          <td>
                            <Pill tone={member.access === "ACTIVE" ? "ok" : "bad"}>{t(`members.access.${member.access}`)}</Pill>
                          </td>
                          <td>
                            <button
                              className={`${s.iconBtn} ${s.iconDanger}`}
                              onClick={() => setModal({ kind: "removeMember", member })}
                              title={t("members.remove")}
                              type="button"
                            >
                              <Trash2 aria-hidden="true" size={13} />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </PortalModal>
      ) : null}

      {toastNode}
    </div>
  );
}
