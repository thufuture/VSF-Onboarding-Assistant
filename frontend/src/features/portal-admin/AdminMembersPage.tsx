"use client";

import { Check, Plus, Search, Trash2, Workflow } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { portalAdminApi } from "@/features/portal-admin/api";
import type {
  AdminMembershipResponseDTO,
  AdminTeamResponseDTO,
  AdminUserResponseDTO,
} from "@/features/portal-admin/dto/responseDTO/admin.response";

import { adminErrorMessage, adminStyles as s, formatDate, Pager, PageHead, paginate, Pill } from "./adminUi";

const PAGE_SIZE = 7;
type AccessFilter = "all" | AdminMembershipResponseDTO["access"];
type Modal = { kind: "add" } | { kind: "remove"; member: AdminMembershipResponseDTO };

/** "Thành viên phòng ban" (v15 `viewAMembers`): ai thuộc phòng ban nào, vai trò, còn truy cập không; gán mới / gỡ. */
export function AdminMembersPage() {
  const t = useTranslations("portalAdmin");
  const [toastNode, showToast] = useToast();

  const [members, setMembers] = useState<AdminMembershipResponseDTO[] | null>(null);
  const [teams, setTeams] = useState<AdminTeamResponseDTO[]>([]);
  const [users, setUsers] = useState<AdminUserResponseDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal | null>(null);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [access, setAccess] = useState<AccessFilter>("all");
  const [page, setPage] = useState(1);
  const [teamId, setTeamId] = useState("");
  const [userId, setUserId] = useState("");

  const reload = useCallback(() => {
    portalAdminApi
      .listMemberships()
      .then(setMembers)
      .catch((caught: unknown) => setError(adminErrorMessage(t, caught)));
  }, [t]);

  useEffect(() => {
    reload();
    portalAdminApi.listTeams().then((r) => setTeams(r.filter((x) => x.is_active))).catch(() => undefined);
    portalAdminApi.listUsers().then((r) => setUsers(r.filter((x) => x.role !== "ADMIN"))).catch(() => undefined);
  }, [reload]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (members ?? []).filter(
      (x) =>
        (access === "all" || x.access === access) &&
        (!q || x.user_name.toLowerCase().includes(q) || x.team_name.toLowerCase().includes(q)),
    );
  }, [members, query, access]);
  const { rows, page: current } = paginate(filtered, page, PAGE_SIZE);

  const taken = useMemo(
    () => new Set((members ?? []).filter((x) => String(x.team_id) === teamId).map((x) => x.user_id)),
    [members, teamId],
  );

  async function run(action: () => Promise<unknown>, done: string) {
    setBusy(true);
    try {
      await action();
      showToast(done);
      reload();
    } catch (caught) {
      setError(adminErrorMessage(t, caught));
    } finally {
      setModal(null);
      setBusy(false);
    }
  }

  return (
    <div className={s.page}>
      <PageHead
        actions={
          <button
            className={s.btn}
            onClick={() => {
              setTeamId(teams[0] ? String(teams[0].id) : "");
              setUserId("");
              setModal({ kind: "add" });
            }}
            type="button"
          >
            <Plus aria-hidden="true" size={14} /> {t("members.assignTitle")}
          </button>
        }
        description={t("members.description")}
        icon={Workflow}
        title={t("members.pageTitle")}
        tone="Teal"
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
              placeholder={t("members.search")}
              value={query}
            />
          </div>
          <div className={s.chips}>
            {(["all", "ACTIVE", "BLOCKED_USER", "BLOCKED_TEAM"] as const).map((key) => (
              <button
                className={`${s.chip} ${access === key ? s.chipOn : ""}`}
                key={key}
                onClick={() => {
                  setAccess(key);
                  setPage(1);
                }}
                type="button"
              >
                {key === "all" ? t("roles.all") : t(`members.access.${key}`)}
              </button>
            ))}
          </div>
        </div>
        <div className={s.tableWrap} style={{ minHeight: PAGE_SIZE * 58 + 41 }}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("users.table.user")}</th>
                <th>{t("members.table.team")}</th>
                <th>{t("members.table.teamRole")}</th>
                <th>{t("members.table.access")}</th>
                <th>{t("members.table.joined")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {members === null ? (
                <tr>
                  <td className={s.emptyCell} colSpan={6}>
                    {t("common.loading")}
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td className={s.emptyCell} colSpan={6}>
                    {t("members.empty")}
                  </td>
                </tr>
              ) : (
                rows.map((member) => (
                  <tr key={`${member.team_id}-${member.user_id}`}>
                    <td style={{ minWidth: 210 }}>
                      <div className={s.cellrow}>
                        <PersonAvatar name={member.user_name} sizePx={30} />
                        <div>
                          <b>{member.user_name}</b>
                          <div className={s.faint}>{t(`roles.${member.user_role}`)}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ minWidth: 180 }}>{member.team_name}</td>
                    <td>{t(`members.teamRole.${member.team_role}`)}</td>
                    <td>
                      <Pill tone={member.access === "ACTIVE" ? "ok" : "bad"}>{t(`members.access.${member.access}`)}</Pill>
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>{formatDate(member.joined_at)}</td>
                    <td>
                      <button
                        className={`${s.iconBtn} ${s.iconDanger}`}
                        onClick={() => setModal({ kind: "remove", member })}
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
        <Pager
          label={t("common.count", { count: filtered.length })}
          onPage={setPage}
          page={current}
          pageSize={PAGE_SIZE}
          total={filtered.length}
        />
      </div>

      {modal?.kind === "add" ? (
        <PortalModal
          closeLabel={t("common.close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("common.cancel")}
              </button>
              <button
                className={m.btn}
                disabled={busy || !teamId || !userId}
                onClick={() =>
                  run(
                    () => portalAdminApi.addMembership({ team_id: Number(teamId), user_id: Number(userId) }),
                    t("members.addedDone"),
                  )
                }
                type="button"
              >
                <Check aria-hidden="true" size={14} /> {t("members.assign")}
              </button>
            </>
          }
          icon={Workflow}
          onClose={() => setModal(null)}
          title={t("members.assignTitle")}
          tone="teal"
        >
          <div className={m.fgrid}>
            <div className={m.span2}>
              <label htmlFor="m-team">{t("members.table.team")}</label>
              <select
                id="m-team"
                onChange={(e) => {
                  setTeamId(e.target.value);
                  setUserId("");
                }}
                value={teamId}
              >
                {teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </select>
            </div>
            <div className={m.span2}>
              <label htmlFor="m-user">{t("members.user")}</label>
              <select id="m-user" onChange={(e) => setUserId(e.target.value)} value={userId}>
                <option value="">{t("members.pickUser")}</option>
                {users
                  .filter((u) => !taken.has(u.id))
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.display_name} ({t(`roles.${u.role}`)})
                    </option>
                  ))}
              </select>
            </div>
            <p className={`${m.span2} ${s.faint}`}>{t("members.roleHint")}</p>
          </div>
        </PortalModal>
      ) : null}

      {modal?.kind === "remove" ? (
        <ConfirmModal
          body={t("members.removeBody", { user: modal.member.user_name, team: modal.member.team_name })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={Trash2}
          confirmLabel={t("members.remove")}
          danger
          icon={Trash2}
          onCancel={() => setModal(null)}
          onConfirm={() =>
            run(
              () => portalAdminApi.removeMembership(modal.member.team_id, modal.member.user_id),
              t("members.removedDone"),
            )
          }
          title={t("members.removeTitle", { user: modal.member.user_name })}
        />
      ) : null}

      {toastNode}
    </div>
  );
}
