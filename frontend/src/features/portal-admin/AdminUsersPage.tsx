"use client";

import { Check, KeyRound, Lock, Pencil, Plus, Search, Unlock, UserPlus, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { useSession } from "@/features/auth/SessionProvider";
import { portalAdminApi } from "@/features/portal-admin/api";
import type { AdminTeamResponseDTO, AdminUserResponseDTO } from "@/features/portal-admin/dto/responseDTO/admin.response";

import { adminErrorMessage, adminStyles as s, formatDateTime, Pager, PageHead, paginate, Pill } from "./adminUi";

const PAGE_SIZE = 6;
type RoleFilter = "all" | "USER" | "HR" | "ADMIN";
type Form = { display_name: string; email: string; role: "USER" | "HR" | "ADMIN"; team_id: string };
type Modal =
  | { kind: "edit"; user: AdminUserResponseDTO | null }
  | { kind: "reset"; user: AdminUserResponseDTO }
  | { kind: "lock"; user: AdminUserResponseDTO }
  | { kind: "secret"; user: AdminUserResponseDTO; password: string };

const EMPTY_FORM: Form = { display_name: "", email: "", role: "USER", team_id: "" };

/** "Người dùng" (v15 `viewAUsers`): tìm + lọc vai trò, sửa, đặt lại mật khẩu, khóa/mở khóa — mọi thao tác đều qua modal xác nhận. */
export function AdminUsersPage() {
  const t = useTranslations("portalAdmin");
  const { user: me } = useSession();
  const [toastNode, showToast] = useToast();

  const [users, setUsers] = useState<AdminUserResponseDTO[] | null>(null);
  const [teams, setTeams] = useState<AdminTeamResponseDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<Form>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<RoleFilter>("all");
  const [page, setPage] = useState(1);

  function reload() {
    portalAdminApi
      .listUsers()
      .then(setUsers)
      .catch((caught: unknown) => setError(adminErrorMessage(t, caught)));
  }

  useEffect(() => {
    reload();
    portalAdminApi
      .listTeams()
      .then((result) => setTeams(result.filter((team) => team.is_active)))
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (users ?? []).filter(
      (u) =>
        (role === "all" || u.role === role) &&
        (!q || u.display_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)),
    );
  }, [users, query, role]);
  const { rows, page: current } = paginate(filtered, page, PAGE_SIZE);

  function openEdit(user: AdminUserResponseDTO | null) {
    setFormError(null);
    setForm(
      user
        ? { display_name: user.display_name, email: user.email, role: user.role, team_id: "" }
        : EMPTY_FORM,
    );
    setModal({ kind: "edit", user });
  }

  async function submitForm(event: FormEvent) {
    event.preventDefault();
    if (modal?.kind !== "edit") return;
    setBusy(true);
    setFormError(null);
    try {
      if (modal.user) {
        await portalAdminApi.updateUser(modal.user.id, {
          display_name: form.display_name,
          email: form.email,
          role: form.role,
        });
        setModal(null);
        showToast(t("users.saved"));
      } else {
        const created = await portalAdminApi.createUser({
          display_name: form.display_name,
          email: form.email,
          role: form.role,
          team_id: form.team_id ? Number(form.team_id) : null,
        });
        setModal({ kind: "secret", user: created.user, password: created.temporary_password });
      }
      reload();
    } catch (caught) {
      setFormError(adminErrorMessage(t, caught));
    } finally {
      setBusy(false);
    }
  }

  async function confirmReset(user: AdminUserResponseDTO) {
    setBusy(true);
    try {
      const result = await portalAdminApi.resetPassword(user.id);
      setModal({ kind: "secret", user, password: result.temporary_password });
    } catch (caught) {
      setModal(null);
      setError(adminErrorMessage(t, caught));
    } finally {
      setBusy(false);
    }
  }

  async function confirmLock(user: AdminUserResponseDTO) {
    setBusy(true);
    try {
      await portalAdminApi.setUserStatus(user.id, user.status === "ACTIVE" ? "INACTIVE" : "ACTIVE");
      setModal(null);
      showToast(user.status === "ACTIVE" ? t("users.locked") : t("users.unlocked"));
      reload();
    } catch (caught) {
      setModal(null);
      setError(adminErrorMessage(t, caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={s.page}>
      <PageHead
        actions={
          <button className={s.btn} onClick={() => openEdit(null)} type="button">
            <Plus aria-hidden="true" size={14} /> {t("users.add")}
          </button>
        }
        description={t("users.description")}
        icon={Users}
        title={t("users.title")}
        tone="Blue"
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
              placeholder={t("users.search")}
              value={query}
            />
          </div>
          <div className={s.chips}>
            {(["all", "USER", "HR", "ADMIN"] as const).map((key) => (
              <button
                className={`${s.chip} ${role === key ? s.chipOn : ""}`}
                key={key}
                onClick={() => {
                  setRole(key);
                  setPage(1);
                }}
                type="button"
              >
                {t(`roles.${key}`)}
              </button>
            ))}
          </div>
        </div>
        <div className={s.tableWrap} style={{ minHeight: PAGE_SIZE * 58 + 41 }}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("users.table.user")}</th>
                <th>{t("users.table.role")}</th>
                <th>{t("users.table.team")}</th>
                <th>{t("users.table.status")}</th>
                <th>{t("users.table.lastLogin")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users === null ? (
                <tr>
                  <td className={s.emptyCell} colSpan={6}>
                    {t("common.loading")}
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td className={s.emptyCell} colSpan={6}>
                    {t("users.empty")}
                  </td>
                </tr>
              ) : (
                rows.map((user) => (
                  <tr key={user.id}>
                    <td style={{ minWidth: 220 }}>
                      <div className={s.cellrow}>
                        <PersonAvatar name={user.display_name} sizePx={32} />
                        <div>
                          <b>{user.display_name}</b>
                          <div className={s.faint}>{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={s.tag}>{t(`roles.${user.role}`)}</span>
                    </td>
                    <td style={{ minWidth: 180 }}>
                      {user.team_names.length ? (
                        user.team_names.map((name) => <div key={name}>{name}</div>)
                      ) : (
                        <span className={s.faint}>{t("users.noTeam")}</span>
                      )}
                    </td>
                    <td>
                      <Pill tone={user.status === "ACTIVE" ? "ok" : "bad"}>
                        {user.status === "ACTIVE" ? t("users.active") : t("users.inactive")}
                      </Pill>
                    </td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {user.last_login_at ? formatDateTime(user.last_login_at) : t("users.neverLoggedIn")}
                    </td>
                    <td>
                      <div className={s.rowActions}>
                        <button className={s.iconBtn} onClick={() => openEdit(user)} title={t("users.edit")} type="button">
                          <Pencil aria-hidden="true" size={13} />
                        </button>
                        <button
                          className={s.iconBtn}
                          onClick={() => setModal({ kind: "reset", user })}
                          title={t("users.resetPassword")}
                          type="button"
                        >
                          <KeyRound aria-hidden="true" size={13} />
                        </button>
                        <button
                          className={`${s.iconBtn} ${user.status === "ACTIVE" ? s.iconDanger : s.iconOk}`}
                          disabled={user.id === me.id}
                          onClick={() => setModal({ kind: "lock", user })}
                          title={user.status === "ACTIVE" ? t("users.lock") : t("users.unlock")}
                          type="button"
                        >
                          {user.status === "ACTIVE" ? (
                            <Lock aria-hidden="true" size={13} />
                          ) : (
                            <Unlock aria-hidden="true" size={13} />
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
              <button className={m.btn} disabled={busy} form="admin-user-form" type="submit">
                <Check aria-hidden="true" size={14} /> {t("common.save")}
              </button>
            </>
          }
          icon={modal.user ? Pencil : UserPlus}
          onClose={() => setModal(null)}
          title={modal.user ? t("users.editTitle") : t("users.add")}
        >
          <form id="admin-user-form" onSubmit={submitForm}>
            <div className={m.fgrid}>
              <div className={m.span2}>
                <label htmlFor="au-name">{t("users.form.name")}</label>
                <input
                  id="au-name"
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  required
                  type="text"
                  value={form.display_name}
                />
              </div>
              <div className={m.span2}>
                <label htmlFor="au-email">{t("users.form.email")}</label>
                <input
                  id="au-email"
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  type="text"
                  value={form.email}
                />
              </div>
              <div>
                <label htmlFor="au-role">{t("users.form.role")}</label>
                <select
                  id="au-role"
                  onChange={(e) => setForm({ ...form, role: e.target.value as Form["role"] })}
                  value={form.role}
                >
                  {(["USER", "HR", "ADMIN"] as const).map((r) => (
                    <option key={r} value={r}>
                      {t(`roles.${r}`)}
                    </option>
                  ))}
                </select>
              </div>
              {modal.user ? null : (
                <div>
                  <label htmlFor="au-team">{t("users.form.team")}</label>
                  <select
                    id="au-team"
                    onChange={(e) => setForm({ ...form, team_id: e.target.value })}
                    value={form.team_id}
                  >
                    <option value="">{t("users.form.noTeam")}</option>
                    {teams.map((team) => (
                      <option key={team.id} value={team.id}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            {modal.user ? null : <p className={s.faint}>{t("users.form.tempHint")}</p>}
            {formError ? <p className={s.banner}>{formError}</p> : null}
          </form>
        </PortalModal>
      ) : null}

      {modal?.kind === "reset" ? (
        <ConfirmModal
          body={t("users.resetBody", { name: modal.user.display_name })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={KeyRound}
          confirmLabel={t("users.resetConfirm")}
          icon={KeyRound}
          onCancel={() => setModal(null)}
          onConfirm={() => confirmReset(modal.user)}
          title={t("users.resetTitle", { name: modal.user.display_name })}
          tone="amber"
          warning={t("users.resetWarning")}
        />
      ) : null}

      {modal?.kind === "lock" ? (
        <ConfirmModal
          body={t(modal.user.status === "ACTIVE" ? "users.lockBody" : "users.unlockBody", {
            name: modal.user.display_name,
          })}
          busy={busy}
          cancelLabel={t("common.cancel")}
          closeLabel={t("common.close")}
          confirmIcon={modal.user.status === "ACTIVE" ? Lock : Unlock}
          confirmLabel={modal.user.status === "ACTIVE" ? t("users.lock") : t("users.unlock")}
          danger={modal.user.status === "ACTIVE"}
          icon={modal.user.status === "ACTIVE" ? Lock : Unlock}
          onCancel={() => setModal(null)}
          onConfirm={() => confirmLock(modal.user)}
          title={t(modal.user.status === "ACTIVE" ? "users.lockTitle" : "users.unlockTitle", {
            name: modal.user.display_name,
          })}
          tone={modal.user.status === "ACTIVE" ? "rose" : "teal"}
        />
      ) : null}

      {modal?.kind === "secret" ? (
        <PortalModal
          closeLabel={t("common.close")}
          footer={
            <button className={m.btn} onClick={() => setModal(null)} type="button">
              {t("common.close")}
            </button>
          }
          icon={KeyRound}
          onClose={() => setModal(null)}
          title={t("users.secretTitle", { name: modal.user.display_name })}
          tone="amber"
        >
          <p className={s.notice}>
            {t("users.secretLabel")} <code>{modal.password}</code>
          </p>
          <p className={s.faint}>{t("users.secretHint")}</p>
        </PortalModal>
      ) : null}

      {toastNode}
    </div>
  );
}
