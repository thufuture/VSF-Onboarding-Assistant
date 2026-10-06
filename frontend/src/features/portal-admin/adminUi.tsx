"use client";

import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { PortalError } from "@/features/portal-hr/api";

import styles from "./AdminShared.module.scss";

export const adminStyles = styles;

export type Tone = "Blue" | "Indigo" | "Teal" | "Amber" | "Rose" | "Slate";

type Translator = ReturnType<typeof useTranslations>;

/** Thông điệp lỗi: mã nghiệp vụ của API nếu có bản dịch, không thì theo loại lỗi chung. */
export function adminErrorMessage(t: Translator, error: unknown): string {
  if (error instanceof PortalError) {
    if (error.apiCode && t.has(`errors.${error.apiCode}`)) return t(`errors.${error.apiCode}`);
    return t(`errors.${error.code}`);
  }
  return t("errors.unavailable");
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.toLocaleDateString("vi-VN")} ${d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN");
}

export function PageHead({
  icon: Icon,
  tone,
  title,
  description,
  actions,
}: {
  icon: LucideIcon;
  tone: Tone;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className={styles.pagehead}>
      <span className={`${styles.phi} ${styles[`tone${tone}`]}`}>
        <Icon aria-hidden="true" size={22} />
      </span>
      <div className={styles.pageheadText}>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions ? <div className={styles.row}>{actions}</div> : null}
    </header>
  );
}

export function IconChip({ icon: Icon, tone, size = 15 }: { icon: LucideIcon; tone: Tone; size?: number }) {
  return (
    <span className={`${styles.ichip} ${styles[`tone${tone}`]}`}>
      <Icon aria-hidden="true" size={size} />
    </span>
  );
}

export function Pill({ tone, children }: { tone: "ok" | "warn" | "bad" | "neutral"; children: ReactNode }) {
  return (
    <span className={styles.pill} data-tone={tone}>
      <i />
      {children}
    </span>
  );
}

export function Kpi({
  label,
  value,
  sub,
  icon,
  tone,
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  icon: LucideIcon;
  tone: Tone;
}) {
  return (
    <div className={styles.kpi}>
      <div className={styles.kh}>
        <small>{label}</small>
        <IconChip icon={icon} tone={tone} />
      </div>
      <b>{value}</b>
      {sub ? <span className={styles.kpiSub}>{sub}</span> : null}
    </div>
  );
}

export function Pager({
  total,
  page,
  pageSize,
  onPage,
  label,
}: {
  total: number;
  page: number;
  pageSize: number;
  onPage: (page: number) => void;
  label: string;
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className={styles.pager}>
      <span>{label}</span>
      {pageCount > 1 ? (
        <div className={styles.pagerButtons}>
          <button disabled={page <= 1} onClick={() => onPage(page - 1)} type="button">
            ‹
          </button>
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
            <button className={n === page ? styles.pagerOn : ""} key={n} onClick={() => onPage(n)} type="button">
              {n}
            </button>
          ))}
          <button disabled={page >= pageCount} onClick={() => onPage(page + 1)} type="button">
            ›
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function paginate<T>(items: T[], page: number, pageSize: number): { rows: T[]; page: number } {
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const current = Math.min(page, pageCount);
  return { rows: items.slice((current - 1) * pageSize, current * pageSize), page: current };
}
