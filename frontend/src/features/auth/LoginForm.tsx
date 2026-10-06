"use client";

import { ArrowRightIcon, EyeClosedIcon, EyeIcon, KeyIcon, MailIcon } from "@primer/octicons-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { resolvePostLoginPath } from "@/features/auth/routing";
import { SessionError, authApi } from "@/features/auth/session";
import { useRouter } from "@/i18n/navigation";

import styles from "./LoginPage.module.scss";

// Kiểm tra sơ bộ ở client; server mới là nơi quyết định email và mật khẩu có hợp lệ hay không.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const ERROR_KEY: Record<SessionError["code"], string> = {
  invalid_credentials: "invalid",
  account_inactive: "inactive",
  rate_limited: "tooMany",
  unavailable: "unavailable",
  network: "unavailable",
};

export function LoginForm() {
  const t = useTranslations("login");
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    // Đọc từ FormData (không từ state) để trình quản lý mật khẩu điền tự động vẫn hoạt động.
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");

    if (!email) return setError(t("errors.emailRequired"));
    if (!EMAIL_PATTERN.test(email)) return setError(t("errors.emailInvalid"));
    if (!password) return setError(t("errors.passwordRequired"));

    setError(null);
    setPending(true);
    try {
      const user = await authApi.login(email, password);
      router.replace(resolvePostLoginPath(user.role, searchParams.get("next")));
    } catch (caught) {
      const code = caught instanceof SessionError ? caught.code : "unavailable";
      setError(t(`errors.${ERROR_KEY[code]}`));
      setPending(false);
    }
  }

  return (
    <form className={styles.form} method="post" onSubmit={submit} noValidate>
      {error ? (
        <div className={styles.error} role="alert">
          <span aria-hidden="true">!</span>
          <span>{error}</span>
        </div>
      ) : null}

      <div className={styles.field}>
        <label htmlFor="login-email">{t("fields.email")}</label>
        <div className={styles.inputControl}>
          <MailIcon aria-hidden="true" size={17} />
          <input
            autoComplete="username"
            className={styles.input}
            disabled={pending}
            id="login-email"
            inputMode="email"
            name="email"
            placeholder={t("fields.emailPlaceholder")}
            type="email"
          />
        </div>
      </div>

      <div className={styles.field}>
        <label htmlFor="login-password">{t("fields.password")}</label>
        <div className={styles.inputControl}>
          <KeyIcon aria-hidden="true" size={17} />
          <input
            autoComplete="current-password"
            className={styles.input}
            disabled={pending}
            id="login-password"
            name="password"
            type={showPassword ? "text" : "password"}
          />
          <button
            aria-label={showPassword ? t("hidePassword") : t("showPassword")}
            aria-pressed={showPassword}
            className={styles.toggle}
            onClick={() => setShowPassword((current) => !current)}
            type="button"
          >
            {showPassword ? <EyeClosedIcon size={17} /> : <EyeIcon size={17} />}
          </button>
        </div>
      </div>

      <button aria-busy={pending} className={styles.submit} disabled={pending} type="submit">
        {pending ? t("submitting") : t("submit")}
        {pending ? null : <ArrowRightIcon size={17} />}
      </button>
    </form>
  );
}
