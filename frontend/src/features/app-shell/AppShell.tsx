"use client";

import {
  BookOpenText,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Moon,
  Sun,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { VsfBrand } from "@/components/brand/VsfBrand";
import { LanguageSwitcher } from "@/components/i18n/LanguageSwitcher";
import { useSession } from "@/features/auth/SessionProvider";
import { Link, usePathname } from "@/i18n/navigation";

import styles from "./AppShell.module.scss";
import { useTheme } from "./useTheme";

type NavItem = { key: string; icon: LucideIcon; href?: string };

// Mục chưa có trang (không có `href`) hiện mờ kèm nhãn "Sắp có" thay vì liên kết chết.
const MEMBER_NAV: NavItem[] = [
  { key: "chat", icon: MessageSquareText, href: "/chat" },
  { key: "documents", icon: BookOpenText },
  { key: "contacts", icon: Users },
  { key: "tickets", icon: LifeBuoy },
];
const STAFF_NAV: NavItem[] = [
  { key: "admin", icon: LayoutDashboard, href: "/admin" },
  { key: "chat", icon: MessageSquareText, href: "/chat" },
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts;
  return letters.map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

/**
 * Khung của khu đã đăng nhập, theo bố cục portal của Ralion: thanh bên (logo, điều hướng theo vai trò, thẻ người dùng,
 * đăng xuất) và vùng làm việc có thanh công cụ (ngôn ngữ, sáng/tối). Điện thoại: thanh bên thành ngăn kéo.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("app");
  const chatText = useTranslations("chat");
  const { user, logout } = useSession();
  const { theme, toggleTheme } = useTheme();
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutFailed, setSignOutFailed] = useState(false);

  // Đổi trang thì đóng ngăn kéo (điều chỉnh state ngay khi vẽ, không cần effect); Escape cũng đóng.
  const [drawerPath, setDrawerPath] = useState(pathname);
  if (drawerPath !== pathname) {
    setDrawerPath(pathname);
    setDrawerOpen(false);
  }
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setDrawerOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    setSignOutFailed(false);
    try {
      await logout();
    } catch {
      setSignOutFailed(true);
      setSigningOut(false);
    }
  }

  const items = user.role === "USER" ? MEMBER_NAV : STAFF_NAV;
  const onChat = pathname.startsWith("/chat");
  const home = user.role === "USER" ? "/chat" : "/admin";

  return (
    <div className={styles.shell} data-theme={theme}>
      <aside className={`${styles.sidebar} ${drawerOpen ? styles.sidebarOpen : ""}`} id="app-sidebar">
        <div className={styles.sidebarHead}>
          <VsfBrand href={home} size={24} />
          <button
            aria-label={t("closeMenu")}
            className={styles.iconButton}
            data-mobile-only
            onClick={() => setDrawerOpen(false)}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <nav aria-label={t("navigation")} className={styles.nav}>
          {items.map(({ key, icon: Icon, href }) => {
            const active = href !== undefined && pathname.startsWith(href);
            if (!href) {
              return (
                <span aria-disabled="true" className={`${styles.navItem} ${styles.navSoon}`} key={key}>
                  <Icon aria-hidden="true" size={18} />
                  <span>{t(`nav.${key}`)}</span>
                  <small>{t("nav.soon")}</small>
                </span>
              );
            }
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`${styles.navItem} ${active ? styles.navActive : ""}`}
                href={href}
                key={key}
              >
                <Icon aria-hidden="true" size={18} />
                <span>{t(`nav.${key}`)}</span>
              </Link>
            );
          })}
        </nav>

        <div className={styles.account}>
          <div className={styles.userCard}>
            <span aria-hidden="true" className={styles.avatar}>
              {initials(user.display_name)}
            </span>
            <span className={styles.userText}>
              <b>{user.display_name}</b>
              <small>{user.department ?? t(`roles.${user.role}`)}</small>
            </span>
          </div>
          <button className={styles.logout} disabled={signingOut} onClick={signOut} type="button">
            <LogOut aria-hidden="true" size={16} />
            <span>{signingOut ? t("signingOut") : t("signOut")}</span>
          </button>
          {signOutFailed ? (
            <p className={styles.signOutError} role="alert">
              {t("signOutFailed")}
            </p>
          ) : null}
        </div>
      </aside>
      {drawerOpen ? <div aria-hidden="true" className={styles.backdrop} onClick={() => setDrawerOpen(false)} /> : null}

      <div className={styles.content}>
        <header className={styles.toolbar}>
          <button
            aria-controls="app-sidebar"
            aria-expanded={drawerOpen}
            aria-label={t("openMenu")}
            className={`${styles.iconButton} ${styles.menuButton}`}
            onClick={() => setDrawerOpen(true)}
            type="button"
          >
            <Menu aria-hidden="true" size={20} />
          </button>
          <div className={styles.pageTitle}>
            {onChat ? (
              <>
                <b>
                  <Sparkles aria-hidden="true" size={18} />
                  {chatText("title")}
                </b>
                <span className={styles.scope}>
                  <ShieldCheck aria-hidden="true" size={14} />
                  {chatText("scope")}
                </span>
              </>
            ) : (
              <b>
                <LayoutDashboard aria-hidden="true" size={18} />
                {t("nav.admin")}
              </b>
            )}
          </div>
          <span className={styles.mobileBrand}>
            <VsfBrand href={home} size={22} />
          </span>
          <div className={styles.toolbarRight}>
            <LanguageSwitcher />
            <button
              aria-label={theme === "dark" ? t("lightMode") : t("darkMode")}
              className={styles.iconButton}
              onClick={toggleTheme}
              title={theme === "dark" ? t("lightMode") : t("darkMode")}
              type="button"
            >
              {theme === "dark" ? <Sun aria-hidden="true" size={18} /> : <Moon aria-hidden="true" size={18} />}
            </button>
          </div>
        </header>
        <div className={styles.page}>{children}</div>
      </div>
    </div>
  );
}
