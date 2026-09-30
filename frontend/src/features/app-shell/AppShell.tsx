"use client";

import { LogOut, Menu, MessageSquareText, PanelLeftClose, PanelLeftOpen, ShieldCheck, Sparkles, Moon, Sun, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { FlatIcon, type FlatIconName } from "@/components/flat-icons/FlatIcon";
import { VsfBrand } from "@/components/brand/VsfBrand";
import { LanguageSwitcher } from "@/components/i18n/LanguageSwitcher";
import { useSession } from "@/features/auth/SessionProvider";
import { Link, usePathname } from "@/i18n/navigation";

import styles from "./AppShell.module.scss";
import { TasksSidebar } from "./TasksSidebar";
import { useSidebarCollapsed } from "./useSidebarCollapsed";
import { useTheme } from "./useTheme";

type NavTone = "blue" | "teal" | "indigo" | "amber" | "rose" | "slate";
type NavItem = { key: string; flat: FlatIconName; href?: string; tone: NavTone };

// Mục chưa có trang (không có `href`) hiện mờ kèm nhãn "Sắp có" thay vì liên kết chết.
const MEMBER_NAV: NavItem[] = [
  { key: "roadmap", flat: "chat", href: "/chat", tone: "blue" },
  { key: "documents", flat: "book", tone: "blue" },
  { key: "contacts", flat: "users", tone: "blue" },
  { key: "tickets", flat: "lifebuoy", tone: "blue" },
];
// Đúng thứ tự nav HR trong prototype v15 (NAV.owner): Tổng quan, Nhân viên, Ticket sự cố, Phản hồi Viga,
// Quản lý task, Tài liệu, Tạo task bằng AI, Đầu mối và đường dẫn. Chỉ mục đã có API thật mới có `href`.
const STAFF_NAV: NavItem[] = [
  { key: "admin", flat: "dashboard", href: "/admin", tone: "blue" },
  { key: "employees", flat: "users", href: "/admin/employees", tone: "blue" },
  { key: "hrTickets", flat: "flag", tone: "blue" },
  { key: "vigaFeedback", flat: "mail", tone: "blue" },
  { key: "taskManagement", flat: "tasks", href: "/admin/tasks", tone: "blue" },
  { key: "documents", flat: "book", href: "/admin/documents", tone: "blue" },
  { key: "aiTasks", flat: "sparkle", href: "/admin/ai-tasks", tone: "blue" },
  { key: "registry", flat: "link", tone: "blue" },
];
// Đúng thứ tự nav Admin trong prototype v15 (NAV.admin): Tổng quan, Người dùng, Phòng ban, Thành viên, Lộ trình mẫu, Nhật ký.
const ADMIN_NAV: NavItem[] = [
  { key: "admin", flat: "dashboard", href: "/admin", tone: "blue" },
  { key: "adminUsers", flat: "user", href: "/admin/users", tone: "blue" },
  { key: "adminTeams", flat: "building", href: "/admin/teams", tone: "blue" },
  { key: "adminMembers", flat: "network", href: "/admin/members", tone: "blue" },
  { key: "adminTemplate", flat: "route", href: "/admin/template", tone: "blue" },
  { key: "adminAudit", flat: "clock", href: "/admin/audit", tone: "blue" },
];

/**
 * Khung của khu đã đăng nhập, theo bố cục portal của Ralion: thanh bên (logo, điều hướng theo vai trò, thẻ người dùng,
 * đăng xuất) và vùng làm việc có thanh công cụ (ngôn ngữ, sáng/tối). Điện thoại: thanh bên thành ngăn kéo.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("app");
  const chatText = useTranslations("chat");
  const brandText = useTranslations("landing.nav");
  const { user, logout } = useSession();
  const { theme, toggleTheme } = useTheme();
  const pathname = usePathname();
  const { collapsed, toggleCollapsed } = useSidebarCollapsed();
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

  const items = user.role === "USER" ? MEMBER_NAV : user.role === "ADMIN" ? ADMIN_NAV : STAFF_NAV;
  const onChat = pathname.startsWith("/chat") && user.role !== "USER";
  const onRoadmap = pathname.startsWith("/chat") && user.role === "USER";
  const home = user.role === "USER" ? "/chat" : "/admin";
  const onTasksTree = user.role !== "USER" && pathname.startsWith("/admin/tasks");
  // Thanh bên thu gọn thì Quản lý task hiện thanh biểu tượng thường (không có cây ngày) để nhường chỗ cho trang.
  const showTree = onTasksTree && !collapsed;
  const collapseButton = (
    <button
      aria-label={collapsed ? t("expandSidebar") : t("collapseSidebar")}
      aria-pressed={collapsed}
      className={styles.collapseButton}
      onClick={toggleCollapsed}
      title={collapsed ? t("expandSidebar") : t("collapseSidebar")}
      type="button"
    >
      {collapsed ? <PanelLeftOpen aria-hidden="true" size={17} /> : <PanelLeftClose aria-hidden="true" size={17} />}
    </button>
  );
  // Mục nav khớp đường dẫn hiện tại (dài nhất trước, ví dụ /admin/documents thắng /admin) — dùng cho tiêu đề thanh trên.
  // Quản lý task (cả khi ADMIN sửa lộ trình mẫu chung) luôn mang tiêu đề "Quản lý task" trên thanh trên.
  const activeItem = onTasksTree
    ? STAFF_NAV.find((i) => i.key === "taskManagement")
    : !onChat
    ? [...items].filter((i) => i.href).sort((a, b) => (b.href?.length ?? 0) - (a.href?.length ?? 0)).find((i) => i.href && pathname.startsWith(i.href))
    : undefined;

  return (
    <div className={styles.shell} data-collapsed={collapsed ? "true" : "false"} data-theme={theme}>
      <aside className={`${styles.sidebar} ${drawerOpen ? styles.sidebarOpen : ""}`} id="app-sidebar">
        <div className={styles.sidebarHead}>
          <Link aria-label={brandText("brand")} className={styles.brand} href={home}>
            <span aria-hidden="true" className={styles.mark}>
              V
            </span>
            <span aria-hidden="true" className={styles.brandText}>
              <b>VSF Onboarding</b>
              <small>{t(`brandSubByRole.${user.role}`)}</small>
            </span>
          </Link>
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

        {showTree ? (
          // Ở Quản lý task không hiện dòng vai trò: "Tổng quan HR" đưa lên đầu và nút thu/mở nằm cùng dòng đó.
          <TasksSidebar toggle={collapseButton} />
        ) : (
          <div className={styles.sideTop}>
            {user.role !== "USER" ? <p className={styles.roleBadge}>{t(`roles.${user.role}`)}</p> : <span />}
            {collapseButton}
          </div>
        )}

        <nav aria-label={t("navigation")} className={styles.nav} hidden={showTree}>
          {items.map(({ key, flat, href, tone }) => {
            const active = activeItem?.key === key;
            if (!href) {
              return (
                <span
                  aria-disabled="true"
                  className={`${styles.navItem} ${styles.navSoon} ${styles[`tone_${tone}`]}`}
                  key={key}
                >
                  <i className={styles.navIcon}>
                    <FlatIcon name={flat} size={26} tone={tone} />
                  </i>
                  <span>{t(`nav.${key}`)}</span>
                  <small>{t("nav.soon")}</small>
                </span>
              );
            }
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`${styles.navItem} ${styles[`tone_${tone}`]} ${active ? styles.navActive : ""}`}
                href={href}
                title={t(`nav.${key}`)}
                key={key}
              >
                <i className={styles.navIcon}>
                  <FlatIcon name={flat} size={26} tone={tone} />
                </i>
                <span>{t(`nav.${key}`)}</span>
              </Link>
            );
          })}
        </nav>

        <div className={styles.account}>
          <div className={styles.userCard}>
            <PersonAvatar name={user.display_name} sizePx={36} />
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
            ) : onRoadmap ? (
              <b>
                <MessageSquareText aria-hidden="true" size={18} />
                {t("nav.roadmap")}
              </b>
            ) : (
              <>
                <span className={styles.crumb}>{t(`roles.${user.role}`)}</span>
              <b>
                <FlatIcon name={activeItem?.flat ?? "dashboard"} size={22} tone={activeItem?.tone ?? "blue"} />
                {t(`nav.${activeItem?.key ?? "admin"}`)}
              </b>
              </>
            )}
          </div>
          <span className={styles.mobileBrand}>
            <VsfBrand href={home} size={19} />
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
        <footer className={styles.pageFoot}>
          <div className={styles.pfLeft}>
            <span className={styles.pfMark}>V</span>
            <div>
              <b>{t("footer.brand")}</b>
              <small>{t("footer.note")}</small>
            </div>
          </div>
          <nav aria-hidden="true" className={styles.pfLinks}>
            <span>{t("footer.help")}</span>
            <span>{t("footer.privacy")}</span>
            <span>{t("footer.terms")}</span>
            <span>{t("footer.contact")}</span>
          </nav>
          <div className={styles.pfRight}>{t("footer.copy")}</div>
        </footer>
      </div>
    </div>
  );
}
