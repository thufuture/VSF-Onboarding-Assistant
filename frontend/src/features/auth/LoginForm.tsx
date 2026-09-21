"use client";

import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type FormEvent, type ReactNode } from "react";

import { resolvePostLoginPath } from "@/features/auth/routing";
import { SessionError, authApi } from "@/features/auth/session";
import { useRouter } from "@/i18n/navigation";

// Kiểm tra sơ bộ ở client; server mới là nơi quyết định email và mật khẩu có hợp lệ hay không.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const ERROR_KEY: Record<SessionError["code"], string> = {
  invalid_credentials: "invalid",
  rate_limited: "tooMany",
  unavailable: "unavailable",
  network: "unavailable",
};

function FieldIcon({ children }: { children: ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="text-ink-3 pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

const INPUT_CLASS =
  "border-border-strong bg-surface text-ink placeholder:text-ink-3 focus:border-accent w-full rounded-md border py-2.5 pr-3 pl-9 transition-colors disabled:opacity-60";

export function LoginForm() {
  const t = useTranslations("login");
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="login-email" className="text-ink text-sm font-medium">
          {t("fields.email")}
        </label>
        <div className="relative">
          <FieldIcon>
            <path d="M4 6h16v12H4V6Zm0 1 8 6 8-6" />
          </FieldIcon>
          <input
            id="login-email"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="username"
            placeholder={t("fields.emailPlaceholder")}
            disabled={pending}
            className={INPUT_CLASS}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="login-password" className="text-ink text-sm font-medium">
          {t("fields.password")}
        </label>
        <div className="relative">
          <FieldIcon>
            <path d="M6 11h12v9H6v-9Zm2 0V8a4 4 0 0 1 8 0v3" />
          </FieldIcon>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            disabled={pending}
            className={INPUT_CLASS}
          />
        </div>
      </div>

      {error ? (
        <p
          role="alert"
          className="border-critical-border bg-critical-bg text-critical rounded-md border px-3 py-2 text-sm"
        >
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        aria-busy={pending}
        className="bg-accent hover:bg-accent-hover flex items-center justify-center gap-2 rounded-md px-4 py-2.5 font-semibold text-white transition-colors disabled:opacity-70"
      >
        {pending ? (
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 animate-spin" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.3" />
            <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
        ) : null}
        {pending ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}
