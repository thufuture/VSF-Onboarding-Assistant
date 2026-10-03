"use client";

import { Bell, Check, ChevronDown, Clock, LockOpen, LogOut, MessageCircle, Moon, Sparkles, Sun, UserRound } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { VigaAvatar } from "@/components/avatar/VigaAvatar";
import { VsfMark } from "@/components/brand/VsfMark";
import { PortalFooter } from "@/components/portal-footer/PortalFooter";
import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { FlagIcon } from "@/components/i18n/LanguageSwitcher";
import { useTheme } from "@/features/app-shell/useTheme";
import { useSession } from "@/features/auth/SessionProvider";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

import styles from "./EmployeeShell.module.scss";
import { useJourney } from "./JourneyProvider";
import { VigaPanel } from "./VigaPanel";
import { useVigaPanel } from "./vigaPanelStore";

// Đúng thứ tự nav nhân viên của prototype v15 (NAV.employee): Tổng quan, Nhiệm vụ, Theo dõi, Tài liệu.
// "Thông báo" nằm ở chuông, các thiết lập (sáng/tối, ngôn ngữ) và "Hồ sơ" nằm trong thẻ tài khoản.
const NAV: {
  key: "overview" | "tasks" | "progress" | "documents" | "tickets";
  href: string;
  icon: FlatIconName;
  tone: FlatTone;
  exact?: boolean;
}[] = [
  { key: "overview", href: "/me", icon: "dashboard", tone: "blue", exact: true },
  { key: "tasks", href: "/me/tasks", icon: "tasks", tone: "indigo" },
  { key: "progress", href: "/me/progress", icon: "route", tone: "green" },
  { key: "documents", href: "/me/documents", icon: "book", tone: "amber" },
  { key: "tickets", href: "/me/tickets", icon: "lifebuoy", tone: "rose" },
];

// Icon theo loại thông báo (màu nằm ở EmployeeShell.module.scss: kind_*).
const KIND_ICONS = { unlocked: LockOpen, done: Check, reminder: Clock, welcome: Sparkles, ticket: MessageCircle } as const;

const LANGUAGES: Locale[] = ["vi", "en"];
const LANGUAGE_NAMES: Record<Locale, string> = { vi: "Việt Nam", en: "English" };

/** Đóng lớp mở xuống khi bấm ra ngoài hoặc bấm Esc. */
function useDismiss(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onClose();
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);
  return ref;
}

/**
 * Khung của nhân viên mới: thanh tiêu đề ngang (logo, mục chức năng, nút Hỏi Viga, chuông có thẻ thông báo, avatar mở
 * thẻ tài khoản gồm hồ sơ, sáng/tối, ngôn ngữ và đăng xuất). Ngăn Hỏi Viga là cột bên phải, mở ra thì trang co lại.
 */
export function EmployeeShell({ children }: { children: ReactNode }) {
  const t = useTranslations("employee");
  const tc = useTranslations("common");
  const { user, logout } = useSession();
  const { theme, toggleTheme } = useTheme();
  const { notifications, unreadCount, markRead, markAllRead } = useJourney();
  const { open: vigaOpen, toggle: toggleViga } = useVigaPanel();
  const pathname = usePathname();
  const router = useRouter();
  const locale = useLocale() as Locale;

  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [bellFilter, setBellFilter] = useState<"all" | "unread">("all");
  const menuRef = useDismiss(menuOpen, () => setMenuOpen(false));
  const bellRef = useDismiss(bellOpen, () => setBellOpen(false));

  // Trang Viga đầy đủ thay cho ngăn bên phải: ẩn ngăn và nút "Hỏi Viga" để không có hai khung trò chuyện cùng lúc.
  const onVigaPage = pathname === "/me/viga" || pathname.startsWith("/me/viga/");
  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);

  const shown = notifications.filter((item) => (bellFilter === "unread" ? !item.read : true));

  function changeLocale(next: Locale) {
    setMenuOpen(false);
    if (next === locale) return;
    router.replace(pathname, { locale: next });
  }

  return (
    <div className={styles.shell} data-theme={theme}>
      <span aria-hidden="true" className={styles.routeBar} key={`bar-${pathname}`} />
      <header className={styles.header}>
        <div className={styles.headerIn}>
          <Link aria-label={t("brand")} className={styles.brand} href="/me">
            <VsfMark className={styles.mark} size={34} />
            <span className={styles.brandText}>
              <b>VSF Onboarding</b>
              <small>{t("brandSub")}</small>
            </span>
          </Link>

          <nav aria-label={t("navLabel")} className={styles.nav}>
            {NAV.map((item) => (
              <Link
                aria-current={isActive(item.href, item.exact) ? "page" : undefined}
                className={`${styles.navLink} ${isActive(item.href, item.exact) ? styles.navOn : ""}`}
                href={item.href}
                key={item.key}
              >
                <FlatIcon name={item.icon} size={20} tone={item.tone} />
                <span>{t(`nav.${item.key}`)}</span>
              </Link>
            ))}
          </nav>

          <div className={styles.tools}>
            {onVigaPage ? null : (
              <button
                aria-expanded={vigaOpen}
                className={`${styles.vigaButton} ${vigaOpen ? styles.vigaOn : ""}`}
                onClick={toggleViga}
                type="button"
              >
                <VigaAvatar sizePx={22} />
                <span>{t("askViga")}</span>
              </button>
            )}

            <div className={styles.dropWrap} ref={bellRef}>
              <button
                aria-expanded={bellOpen}
                aria-label={t("nav.notifications")}
                className={`${styles.iconButton} ${bellOpen ? styles.iconOn : ""}`}
                onClick={() => setBellOpen((open) => !open)}
                type="button"
              >
                <Bell aria-hidden="true" size={16} />
                {unreadCount > 0 ? <span className={styles.badge}>{unreadCount}</span> : null}
              </button>

              {bellOpen ? (
                <div aria-label={t("nav.notifications")} className={`${styles.card} ${styles.bellCard}`} role="menu">
                  <div className={styles.cardHead}>
                    <b>{t("nav.notifications")}</b>
                    <button disabled={unreadCount === 0} onClick={markAllRead} type="button">
                      <Check aria-hidden="true" size={13} /> {t("notifications.markAll")}
                    </button>
                  </div>

                  <div className={styles.bellTabs} role="tablist">
                    {(["all", "unread"] as const).map((key) => (
                      <button
                        aria-selected={bellFilter === key}
                        className={bellFilter === key ? styles.bellTabOn : ""}
                        key={key}
                        onClick={() => setBellFilter(key)}
                        role="tab"
                        type="button"
                      >
                        {t(key === "all" ? "notifications.filterAll" : "notifications.filterUnread", {
                          count: key === "all" ? notifications.length : unreadCount,
                        })}
                      </button>
                    ))}
                  </div>

                  {shown.length === 0 ? (
                    <p className={styles.cardEmpty}>{t("notifications.emptyTitle")}</p>
                  ) : (
                    <ul className={styles.bellList}>
                      {shown.map((item) => {
                        const Icon = KIND_ICONS[item.kind];
                        return (
                          <li key={item.id}>
                            <button
                              className={`${styles.bellItem} ${item.read ? styles.bellRead : styles.bellUnread}`}
                              onClick={() => {
                                markRead(item.id);
                                if (item.taskId) {
                                  setBellOpen(false);
                                  router.push(`/me/tasks/${item.taskId}`);
                                } else if (item.href) {
                                  setBellOpen(false);
                                  router.push(item.href);
                                }
                              }}
                              role="menuitem"
                              title={item.title}
                              type="button"
                            >
                              <span className={`${styles.bellIcon} ${styles[`kind_${item.kind}`]}`}>
                                <Icon aria-hidden="true" size={16} />
                              </span>
                              <span className={styles.bellText}>
                                <span className={styles.bellKind}>{t(`notifications.kind.${item.kind}`)}</span>
                                <span className={styles.bellTitle}>{item.title}</span>
                                <span className={styles.bellBody}>{item.body}</span>
                              </span>
                              {item.read ? null : <i aria-label={t("notifications.unreadMark")} className={styles.bellDot} />}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              ) : null}
            </div>

            <div className={styles.dropWrap} ref={menuRef}>
              <button
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-label={t("accountMenu")}
                className={styles.avatarButton}
                onClick={() => setMenuOpen((open) => !open)}
                type="button"
              >
                <PersonAvatar name={user.display_name} sizePx={32} />
                <span className={styles.avatarName}>{user.display_name}</span>
                <ChevronDown aria-hidden="true" className={styles.chev} size={14} />
              </button>

              {menuOpen ? (
                <div aria-label={t("accountMenu")} className={`${styles.card} ${styles.menu}`} role="menu">
                  <div className={styles.menuHead}>
                    <PersonAvatar name={user.display_name} sizePx={44} />
                    <div>
                      <b>{user.display_name}</b>
                      <small>{user.email}</small>
                      {user.department ? <span className={styles.dept}>{user.department}</span> : null}
                    </div>
                  </div>

                  <Link className={styles.menuItem} href="/me/profile" onClick={() => setMenuOpen(false)} role="menuitem">
                    <UserRound aria-hidden="true" size={16} /> {t("menu.profile")}
                  </Link>

                  <div className={styles.menuGroup}>
                    <span className={styles.menuLabel}>{t("menu.appearance")}</span>
                    <button className={styles.menuItem} onClick={toggleTheme} role="menuitem" type="button">
                      {theme === "dark" ? <Sun aria-hidden="true" size={16} /> : <Moon aria-hidden="true" size={16} />}
                      {theme === "dark" ? t("lightMode") : t("darkMode")}
                    </button>
                  </div>

                  <div className={styles.menuGroup}>
                    <span className={styles.menuLabel}>{tc("language")}</span>
                    {LANGUAGES.map((option) => (
                      <button
                        aria-current={option === locale ? "true" : undefined}
                        className={`${styles.menuItem} ${option === locale ? styles.menuItemOn : ""}`}
                        key={option}
                        onClick={() => changeLocale(option)}
                        role="menuitem"
                        type="button"
                      >
                        <FlagIcon locale={option} />
                        {LANGUAGE_NAMES[option]}
                        {option === locale ? <Check aria-hidden="true" className={styles.menuCheck} size={14} /> : null}
                      </button>
                    ))}
                  </div>

                  <button className={`${styles.menuItem} ${styles.menuLogout}`} onClick={() => void logout()} role="menuitem" type="button">
                    <LogOut aria-hidden="true" size={16} /> {t("menu.logout")}
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      <div className={styles.body}>
        <main className={styles.main} key={pathname}>
          {children}

          <PortalFooter />
        </main>

        {onVigaPage ? null : <VigaPanel />}
      </div>
    </div>
  );
}
