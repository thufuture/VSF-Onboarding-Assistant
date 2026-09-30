"use client";

import { KeyRound, Loader2, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { useToast } from "@/components/portal-modal/PortalModal";
import { useSession } from "@/features/auth/SessionProvider";
import { PortalError, portalHrApi } from "@/features/portal-hr/api";
import type { EmployeeProfileResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import shared from "./employee.module.scss";
import { PageHero } from "./PageHero";
import styles from "./ProfilePage.module.scss";

/** "Hồ sơ của tôi": thông tin tài khoản, tiến độ lộ trình, đổi tên hiển thị và đổi mật khẩu. */
export function EmployeeProfilePage() {
  const t = useTranslations("employee.profile");
  const { user } = useSession();
  const [profile, setProfile] = useState<EmployeeProfileResponseDTO | null>(null);
  const [failed, setFailed] = useState(false);
  const [name, setName] = useState(user.display_name);
  const [savingName, setSavingName] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [toastNode, showToast] = useToast();

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .getMyProfile()
      .then((result) => {
        if (cancelled) return;
        setProfile(result);
        setName(result.display_name);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSaveName(event: FormEvent) {
    event.preventDefault();
    setSavingName(true);
    try {
      const updated = await portalHrApi.updateMyProfile(name);
      setProfile(updated);
      showToast(t("nameSaved"));
    } catch {
      showToast(t("nameFailed"));
    } finally {
      setSavingName(false);
    }
  }

  async function onChangePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    if (next !== confirm) {
      setPasswordError(t("password.mismatch"));
      return;
    }
    if (next.length < 8) {
      setPasswordError(t("password.tooShort"));
      return;
    }
    setSavingPassword(true);
    try {
      await portalHrApi.changeMyPassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      showToast(t("password.saved"));
    } catch (caught) {
      const code = caught instanceof PortalError ? caught.apiCode : null;
      setPasswordError(
        code === "CURRENT_PASSWORD_WRONG"
          ? t("password.wrongCurrent")
          : code === "PASSWORD_UNCHANGED"
            ? t("password.unchanged")
            : t("password.failed"),
      );
    } finally {
      setSavingPassword(false);
    }
  }

  const pct = profile && profile.tasks_total > 0 ? Math.round((profile.tasks_done / profile.tasks_total) * 100) : 0;

  return (
    <>
      <PageHero
        avatarName={user.display_name}
        compact
        subtitle={t("subtitle")}
        title={t("title")}
      />

      <div className={shared.container}>
        {failed ? <p className={shared.banner}>{t("failed")}</p> : null}

        <div className={styles.columns}>
          <section className={`${shared.card} ${shared.rise} ${styles.identity}`}>
            <PersonAvatar name={profile?.display_name ?? user.display_name} sizePx={84} />
            <h2>{profile?.display_name ?? user.display_name}</h2>
            <p>{profile?.email ?? user.email}</p>
            <div className={styles.badges}>
              <span className={shared.tagBlue}>{t(`role.${profile?.role ?? user.role}`)}</span>
              {profile?.department ? <span className={shared.tag}>{profile.department}</span> : null}
            </div>

            <dl className={styles.facts}>
              <div>
                <dt>{t("facts.joined")}</dt>
                <dd>{profile ? new Date(profile.joined_at).toLocaleDateString() : "—"}</dd>
              </div>
              <div>
                <dt>{t("facts.started")}</dt>
                <dd>{profile?.journey_started_at ? new Date(profile.journey_started_at).toLocaleDateString() : t("facts.notStarted")}</dd>
              </div>
              <div>
                <dt>{t("facts.lastLogin")}</dt>
                <dd>{profile?.last_login_at ? new Date(profile.last_login_at).toLocaleString() : "—"}</dd>
              </div>
            </dl>

            <div className={styles.progress}>
              <div className={styles.progressHead}>
                <span>{t("progressLabel")}</span>
                <b>{pct}%</b>
              </div>
              <div className={shared.meter}>
                <i style={{ width: `${pct}%` }} />
              </div>
              <small>
                {t("progressHint", {
                  done: profile?.tasks_done ?? 0,
                  total: profile?.tasks_total ?? 0,
                  requiredDone: profile?.required_done ?? 0,
                  requiredTotal: profile?.required_total ?? 0,
                })}
              </small>
            </div>
          </section>

          <div className={styles.forms}>
            <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 1 } as never}>
              <div className={shared.cardHead}>
                <div>
                  <h2>{t("nameTitle")}</h2>
                  <small>{t("nameHint")}</small>
                </div>
                <FlatIcon name="user" size={26} tone="blue" />
              </div>
              <form className={styles.form} onSubmit={onSaveName}>
                <label>
                  <span>{t("nameLabel")}</span>
                  <input maxLength={120} onChange={(event) => setName(event.target.value)} required value={name} />
                </label>
                <div className={styles.formFoot}>
                  <button className={shared.btn} disabled={savingName || !name.trim()} type="submit">
                    {savingName ? <Loader2 aria-hidden="true" className={styles.spin} size={14} /> : <Save aria-hidden="true" size={14} />}{" "}
                    {t("save")}
                  </button>
                </div>
              </form>
            </section>

            <section className={`${shared.card} ${shared.rise}`} style={{ "--i": 2 } as never}>
              <div className={shared.cardHead}>
                <div>
                  <h2>{t("password.title")}</h2>
                  <small>{t("password.hint")}</small>
                </div>
                <KeyRound aria-hidden="true" className={styles.headIcon} size={22} />
              </div>
              <form className={styles.form} onSubmit={onChangePassword}>
                <label>
                  <span>{t("password.current")}</span>
                  <input autoComplete="current-password" onChange={(event) => setCurrent(event.target.value)} required type="password" value={current} />
                </label>
                <div className={styles.pair}>
                  <label>
                    <span>{t("password.new")}</span>
                    <input autoComplete="new-password" minLength={8} onChange={(event) => setNext(event.target.value)} required type="password" value={next} />
                  </label>
                  <label>
                    <span>{t("password.confirm")}</span>
                    <input autoComplete="new-password" minLength={8} onChange={(event) => setConfirm(event.target.value)} required type="password" value={confirm} />
                  </label>
                </div>
                {passwordError ? <p className={styles.error}>{passwordError}</p> : null}
                <div className={styles.formFoot}>
                  <small>{t("password.note")}</small>
                  <button className={shared.btn} disabled={savingPassword} type="submit">
                    {savingPassword ? <Loader2 aria-hidden="true" className={styles.spin} size={14} /> : <KeyRound aria-hidden="true" size={14} />}{" "}
                    {t("password.submit")}
                  </button>
                </div>
              </form>
            </section>
          </div>
        </div>
      </div>
      {toastNode}
    </>
  );
}
