"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { authApi } from "@/features/auth/session";
import { useRouter } from "@/i18n/navigation";

// Phiên sống 30 phút; hỏi gia hạn mỗi 5 phút khi tab đang mở (backend chỉ cấp cookie mới khi đã quá nửa thời hạn).
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

type SessionContextValue = {
  user: SessionUserResponseDTO;
  logout: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

/** Giữ người dùng đã xác thực ở server, gia hạn phiên định kỳ và đưa về trang đăng nhập khi phiên mất hiệu lực. */
export function SessionProvider({ initialUser, children }: { initialUser: SessionUserResponseDTO; children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState(initialUser);

  const toLogin = useCallback(() => router.replace("/login"), [router]);

  useEffect(() => {
    let stopped = false;

    async function renew() {
      if (document.visibilityState !== "visible") return;
      try {
        const next = await authApi.refresh();
        if (stopped) return;
        if (next === null) toLogin();
        else setUser(next);
      } catch {
        // Lỗi mạng tạm thời: giữ nguyên, lần sau thử lại.
      }
    }

    const timer = window.setInterval(renew, REFRESH_INTERVAL_MS);
    document.addEventListener("visibilitychange", renew);
    return () => {
      stopped = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", renew);
    };
  }, [toLogin]);

  const logout = useCallback(async () => {
    await authApi.logout();
    toLogin();
  }, [toLogin]);

  const value = useMemo(() => ({ user, logout }), [user, logout]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
