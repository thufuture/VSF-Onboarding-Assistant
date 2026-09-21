"use client";

import {
  ArrowRight,
  Bot,
  Braces,
  Brain,
  Check,
  CircleHelp,
  ClipboardList,
  Container,
  Database,
  Headset,
  LayoutList,
  Mail,
  MessageSquare,
  Search,
  Send,
  ShieldCheck,
  Ticket,
  Users,
  Workflow,
} from "lucide-react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { VsfBrand } from "@/components/brand/VsfBrand";
import { Link } from "@/i18n/navigation";

import styles from "./LandingPage.module.css";

type SectionId = "hero" | "how" | "roles";
type T = ReturnType<typeof useTranslations>;

const SERVICE_KEYS = ["chat", "process", "clarify", "ticket"] as const;
const FEATURE_KEYS = ["chat", "process", "ticket"] as const;
const ROLE_KEYS = ["asker", "hr", "team", "admin"] as const;
const TECH_KEYS = ["web", "api", "db", "search", "embed", "llm", "docker"] as const;
const PROCESS_STEP_KEYS = ["s1", "s2", "s3", "s4"] as const;
const TICKET_KPI_KEYS = ["k1", "k2", "k3"] as const;
const TICKET_STATE_KEYS = ["m1", "m2", "m3", "m4"] as const;

const SERVICE_ICONS: Record<(typeof SERVICE_KEYS)[number], { icon: ReactNode; color: string; bg: string }> = {
  chat: { icon: <MessageSquare size={24} />, color: "#0057B8", bg: "#DAE6FF" },
  process: { icon: <LayoutList size={24} />, color: "#4628A4", bg: "#EFEAFF" },
  clarify: { icon: <CircleHelp size={24} />, color: "#5FC400", bg: "#ECFFDA" },
  ticket: { icon: <Ticket size={24} />, color: "#BB3800", bg: "#FFE5DA" },
};

const ROLE_STYLES: Record<(typeof ROLE_KEYS)[number], { icon: ReactNode; color: string; bg: string }> = {
  asker: { icon: <Users size={22} />, color: "#08A995", bg: "#E6FBF7" },
  hr: { icon: <ClipboardList size={22} />, color: "#7C3AED", bg: "#F3EEFF" },
  team: { icon: <Headset size={22} />, color: "#1090CB", bg: "#E6F4FF" },
  admin: { icon: <ShieldCheck size={22} />, color: "#D95D00", bg: "#FFF2E8" },
};

const TECH_ICONS: Record<(typeof TECH_KEYS)[number], ReactNode> = {
  web: <Braces size={23} />,
  api: <Workflow size={23} />,
  db: <Database size={23} />,
  search: <Search size={23} />,
  embed: <Brain size={23} />,
  llm: <Bot size={23} />,
  docker: <Container size={23} />,
};

/* ─── Mockup: hỏi đáp có nguồn ─────────────────────────────── */
function ChatMockup({ t }: { t: T }) {
  return (
    <div className={styles.appMockup}>
      <div className={styles.appBar}>
        <div className={styles.trafficDots}>
          <span className={styles.trafficDot} style={{ background: "#FF5F57" }} />
          <span className={styles.trafficDot} style={{ background: "#FEBC2E" }} />
          <span className={styles.trafficDot} style={{ background: "#28C840" }} />
        </div>
        <div className={styles.appBarCenter}>
          <Search size={12} className={styles.appBarSearchIcon} />
          <span className={styles.appBarTitle}>{t("mock.chat.title")}</span>
        </div>
        <span className={styles.appBadge}>
          <span className={styles.liveDot} />
          {t("mock.chat.badge")}
        </span>
      </div>

      <div className={styles.appBody}>
        <aside className={styles.appSidebar}>
          <span className={styles.sideLogoR}>V</span>
          <span className={`${styles.sideItem} ${styles.sideItemActive}`} />
          <span className={styles.sideItem} />
          <span className={styles.sideItem} />
          <span className={styles.sideItem} />
        </aside>

        <div className={styles.appConvo}>
          <p className={styles.convoLabel}>{t("mock.chat.label")}</p>
          <div className={styles.convoQ}>{t("mock.chat.question")}</div>
          <div className={styles.convoA}>
            <span className={styles.convoAvatar}>V</span>
            <div className={styles.convoAnswer}>
              <strong>{t("mock.chat.assistant")}</strong>
              <p>{t("mock.chat.answer")}</p>
              <div className={styles.convoCites}>
                <span>{t("mock.chat.cite")}</span>
              </div>
            </div>
          </div>
          <div className={styles.convoSources}>
            <span className={styles.sourceAvatars}>
              <i />
            </span>
            {t("mock.chat.sources")}
          </div>
          <div className={styles.mockInputBar}>
            <span className={styles.mockInputPlaceholder}>{t("mock.chat.placeholder")}</span>
            <button className={styles.mockSendBtn} type="button" aria-label={t("mock.chat.send")}>
              <Send size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Mockup: quy trình, link, đầu mối, biểu mẫu ────────────── */
function ProcessMockup({ t }: { t: T }) {
  return (
    <div className={styles.planMockup}>
      <div className={styles.planHead}>
        <span className={styles.planBadge}>{t("mock.process.badge")}</span>
        <span className={styles.planName}>{t("mock.process.name")}</span>
        <span className={styles.planVer}>{t("mock.process.version")}</span>
      </div>
      <div className={styles.planList}>
        {PROCESS_STEP_KEYS.map((key, index) => (
          <div className={`${styles.planTask} ${index === 0 ? styles.planActive : ""}`} key={key}>
            <span className={styles.planCb} />
            <div>
              <small>{t(`mock.process.${key}.cat`)}</small>
              <p>{t(`mock.process.${key}.label`)}</p>
            </div>
          </div>
        ))}
      </div>
      <div className={styles.planFoot}>
        <span>{t("mock.process.foot")}</span>
        <button className={styles.planBtn} type="button">
          {t("mock.process.button")}
        </button>
      </div>
    </div>
  );
}

/* ─── Mockup: ticket nháp, bạn xác nhận trước khi gửi ────────── */
function TicketMockup({ t }: { t: T }) {
  return (
    <div className={styles.dashMockup}>
      <div className={styles.dashHead}>
        <strong>{t("mock.ticket.title")}</strong>
        <span className={styles.dashProject}>{t("mock.ticket.team")}</span>
      </div>
      <div className={styles.dashKpis}>
        {TICKET_KPI_KEYS.map((key) => (
          <div className={styles.dashKpi} key={key}>
            <span style={{ color: "#1090CB", fontSize: "1.05rem" }}>{t(`mock.ticket.${key}.value`)}</span>
            <small>{t(`mock.ticket.${key}.label`)}</small>
          </div>
        ))}
      </div>
      <div className={styles.dashMiles}>
        {TICKET_STATE_KEYS.map((key, index) => (
          <div
            className={`${styles.dashMile} ${index < 2 ? styles.mileDone : ""} ${index === 2 ? styles.mileActive : ""}`}
            key={key}
          >
            {t(`mock.ticket.${key}`)}
          </div>
        ))}
      </div>
      <div className={styles.dashBar}>
        <div style={{ width: "60%" }} />
      </div>
    </div>
  );
}

export function LandingPage() {
  const t = useTranslations("landing");
  const [activeSection, setActiveSection] = useState<SectionId>("hero");
  const [atTop, setAtTop] = useState(true);
  const pendingNavTarget = useRef<SectionId | null>(null);

  /* Đánh dấu mục đang xem và trạng thái "đầu trang" (header trong suốt trên ảnh nền). */
  useEffect(() => {
    const update = () => {
      setAtTop(window.scrollY < 24);
      // Coi mục nằm ở vùng đọc phía trên là mục đang xem; mốc cố định làm cuộn mượt ghi đè mục vừa bấm.
      const readingZone = Math.max(170, Math.min(window.innerHeight * 0.38, 380));
      const marker = window.scrollY + readingZone;
      const pageTop = (id: string) => {
        const element = document.getElementById(id);
        return element ? element.getBoundingClientRect().top + window.scrollY : Number.POSITIVE_INFINITY;
      };
      if (pendingNavTarget.current) {
        const pending = pendingNavTarget.current;
        const target = document.getElementById(pending);
        const arrived =
          pending === "hero"
            ? window.scrollY < 24
            : Boolean(target && target.getBoundingClientRect().top <= readingZone);
        if (!arrived) return;
        pendingNavTarget.current = null;
      }
      setActiveSection(marker >= pageTop("roles") ? "roles" : marker >= pageTop("how") ? "how" : "hero");
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  /* Hiện dần các khối khi cuộn tới (IntersectionObserver). */
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add(styles.visible);
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" },
    );
    document.querySelectorAll("[data-aos]").forEach((element) => io.observe(element));
    return () => io.disconnect();
  }, []);

  const navLink = (id: SectionId) => `${styles.navLinkItem} ${activeSection === id ? styles.navLinkActive : ""}`;
  function selectSection(id: SectionId) {
    pendingNavTarget.current = id;
    setActiveSection(id);
  }

  const mockups: Record<(typeof FEATURE_KEYS)[number], ReactNode> = {
    chat: <ChatMockup t={t} />,
    process: <ProcessMockup t={t} />,
    ticket: <TicketMockup t={t} />,
  };

  return (
    <div className={styles.page}>
      <a href="#main" className={styles.skipLink}>
        {t("skipLink")}
      </a>

      {/* ─── HEADER ─── */}
      <header className={`${styles.header} ${atTop ? styles.headerTop : ""}`}>
        <nav className={styles.nav} aria-label={t("nav.label")}>
          <span className={styles.brand}>
            <VsfBrand href="/#hero" size={28} />
          </span>

          <div className={styles.navLinks}>
            <Link
              aria-current={activeSection === "hero" ? "page" : undefined}
              className={navLink("hero")}
              href="/#hero"
              onClick={() => selectSection("hero")}
            >
              {t("nav.top")}
            </Link>
            <a
              aria-current={activeSection === "how" ? "page" : undefined}
              className={navLink("how")}
              href="#how"
              onClick={() => selectSection("how")}
            >
              {t("nav.how")}
            </a>
            <a
              aria-current={activeSection === "roles" ? "page" : undefined}
              className={navLink("roles")}
              href="#roles"
              onClick={() => selectSection("roles")}
            >
              {t("nav.roles")}
            </a>
          </div>

          <div className={styles.navRight}>
            <Link className={styles.loginBtn} href="/login">
              {t("nav.login")}
            </Link>
          </div>
        </nav>
      </header>

      <main id="main">
        {/* ─── HERO: ảnh Vincom Center Đồng Khởi + lớp phủ xanh đậm ─── */}
        <section className={styles.hero} id="hero">
          <Image
            src="/images/landing/hero-vincom-dong-khoi.webp"
            alt={t("hero.photoAlt")}
            fill
            priority
            sizes="100vw"
            className={styles.heroPhoto}
          />
          <div className={styles.heroShade} aria-hidden="true" />

          <div className={styles.heroContent}>
            <p className={styles.heroBadge}>{t("hero.badge")}</p>
            <h1 className={styles.heroTitle}>
              {t("hero.line1")}
              <br />
              {t("hero.line2")}
            </h1>
            <p className={styles.heroSub}>{t("hero.description")}</p>

            <div className={styles.heroCtas}>
              <Link className={styles.btnPrimary} href="/login">
                {t("hero.primary")}
                <ArrowRight size={18} />
              </Link>
              <a className={styles.btnLight} href="#how" onClick={() => selectSection("how")}>
                {t("hero.secondary")}
              </a>
            </div>

            <ul className={styles.heroChecks}>
              <li>
                <Check size={16} className={styles.checkIcon} />
                {t("hero.checkSources")}
              </li>
              <li>
                <Check size={16} className={styles.checkIcon} />
                {t("hero.checkProcess")}
              </li>
            </ul>
          </div>

          <p className={styles.heroCredit}>
            {t("hero.creditLead")}{" "}
            <a
              href="https://commons.wikimedia.org/wiki/File:Ho_Chi_Minh_City,_Vincom_Center,_2020-01_CN-01.jpg"
              target="_blank"
              rel="noopener noreferrer"
            >
              {t("hero.creditAuthor")}
            </a>
            ,{" "}
            <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener noreferrer">
              {t("hero.creditLicense")}
            </a>
            , {t("hero.creditSource")} ({t("hero.creditEdited")})
          </p>
        </section>

        {/* ─── DỊCH VỤ ─── */}
        <section className={styles.servicesSection} id="what-we-do">
          <div className={styles.servicesGrid}>
            {SERVICE_KEYS.map((key, index) => (
              <div
                className={`${styles.svcCard} ${styles.animUp}`}
                data-aos=""
                key={key}
                style={{ transitionDelay: `${index * 70}ms` }}
              >
                <span
                  className={styles.svcIcon}
                  style={{ background: SERVICE_ICONS[key].bg, color: SERVICE_ICONS[key].color }}
                >
                  {SERVICE_ICONS[key].icon}
                </span>
                <div className={styles.svcText}>
                  <strong>{t(`services.${key}.title`)}</strong>
                  <span>{t(`services.${key}.sub`)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ─── GIỚI THIỆU (bắt đầu mục "Cách hoạt động") ─── */}
        <section className={styles.introSection} id="how">
          <div className={`${styles.introInner} ${styles.animUp}`} data-aos="">
            <h2>{t("intro.heading")}</h2>
            <p>{t("intro.text")}</p>
          </div>
        </section>

        {/* ─── BA TÍNH NĂNG, MỖI TÍNH NĂNG MỘT MOCKUP ─── */}
        <section className={styles.featuresSection}>
          {FEATURE_KEYS.map((key, index) => (
            <div
              className={`${styles.featRow} ${index === 1 ? styles.featReverse : ""} ${styles.animUp}`}
              data-aos=""
              key={key}
              style={{ transitionDelay: "50ms" }}
            >
              <div className={styles.featCopy}>
                <div className={styles.featLabel}>
                  <span
                    className={styles.featIconBadge}
                    style={{ background: `${SERVICE_ICONS[key].color}22`, color: SERVICE_ICONS[key].color }}
                  >
                    {SERVICE_ICONS[key].icon}
                  </span>
                  <div>
                    <strong>{t(`features.${key}.label`)}</strong>
                    <small>{t(`features.${key}.sub`)}</small>
                  </div>
                </div>
                <h3>
                  {t(`features.${key}.titleStart`)}{" "}
                  <span className={styles.accent}>{t(`features.${key}.titleAccent`)}</span>
                  {/^[,.;:!?]/.test(t(`features.${key}.titleEnd`)) ? "" : " "}
                  {t(`features.${key}.titleEnd`)}
                </h3>
                <p>{t(`features.${key}.body`)}</p>
              </div>
              <div className={styles.featMedia}>
                <div className={styles.mockWrap}>
                  {mockups[key]}
                  {key === "chat" ? <p className={styles.mockCaption}>{t("mock.sample")}</p> : null}
                </div>
              </div>
            </div>
          ))}
        </section>

        {/* ─── VAI TRÒ ─── */}
        <section className={styles.rolesSection}>
          <div className={`${styles.rolesHeader} ${styles.animUp}`} data-aos="" id="roles">
            <h2>{t("roles.title")}</h2>
            <p>{t("roles.lead")}</p>
            <span className={styles.rolesFlowLabel}>{t("roles.flow")}</span>
          </div>

          <div aria-label={t("roles.flow")} className={styles.rolesGrid}>
            {ROLE_KEYS.map((key, index) => (
              <article
                className={`${styles.roleCard} ${styles.animUp}`}
                data-aos=""
                key={key}
                style={{ transitionDelay: `${index * 60}ms` }}
              >
                <div className={styles.roleCardTop}>
                  <span
                    className={styles.roleIconWrap}
                    style={{ background: ROLE_STYLES[key].bg, color: ROLE_STYLES[key].color }}
                  >
                    {ROLE_STYLES[key].icon}
                  </span>
                  <span
                    className={styles.roleTag}
                    style={{ color: ROLE_STYLES[key].color, background: ROLE_STYLES[key].bg }}
                  >
                    {t(`roles.${key}.tag`)}
                  </span>
                </div>
                <h3>{t(`roles.${key}.title`)}</h3>
                <p>{t(`roles.${key}.body`)}</p>
                <Link className={styles.roleBtn} href="/login">
                  {t(`roles.${key}.cta`)} <ArrowRight size={14} />
                </Link>
              </article>
            ))}
          </div>
        </section>

        {/* ─── NỀN TẢNG ─── */}
        <section className={styles.techSection}>
          <p className={`${styles.techTitle} ${styles.animUp}`} data-aos="">
            {t("tech.title")}
          </p>
          <div className={`${styles.techRow} ${styles.animUp}`} data-aos="">
            {TECH_KEYS.map((key) => (
              <article className={styles.techBadge} key={key}>
                <span className={styles.techIcon}>{TECH_ICONS[key]}</span>
                <span>
                  <strong>{t(`tech.${key}.name`)}</strong>
                  <small>{t(`tech.${key}.detail`)}</small>
                </span>
              </article>
            ))}
          </div>
        </section>

        {/* ─── KÊU GỌI HÀNH ĐỘNG ─── */}
        <section className={styles.nlSection}>
          <div className={`${styles.nlInner} ${styles.animUp}`} data-aos="">
            <h2>{t("cta.heading")}</h2>
            <p>{t("cta.text")}</p>
            <Link className={styles.btnPrimaryLg} href="/login">
              {t("cta.button")} <ArrowRight size={16} />
            </Link>
          </div>
        </section>
      </main>

      {/* ─── FOOTER ─── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <span className={styles.footerLogo}>{t("nav.brand")}</span>
            <p>{t("footer.tagline")}</p>
            <a className={styles.footerMail} href={`mailto:${t("footer.email")}`}>
              <Mail size={13} />
              {t("footer.email")}
            </a>
          </div>

          <div className={styles.footerCol}>
            <strong>{t("footer.aboutTitle")}</strong>
            <a href="#how">{t("footer.how")}</a>
            <a href="#roles">{t("footer.roles")}</a>
            <Link href="/login">{t("footer.login")}</Link>
          </div>

          <div className={styles.footerCol}>
            <strong>{t("footer.contactTitle")}</strong>
            <p>{t("footer.contactLine")}</p>
            <span>{t("footer.contactNote")}</span>
          </div>
        </div>

        <div className={styles.footerBottom}>
          <span>{t("footer.copyright")}</span>
        </div>
      </footer>
    </div>
  );
}
