"use client";

import { Eye, Mail, Search, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type { EmployeeSummaryResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./EmployeesPage.module.scss";

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) return t(`errors.${error.code}`);
  return t("errors.unavailable");
}

const PAGE_SIZE = 5;

type Filter = "all" | "attn" | "wait" | "ok";

function statusOf(employee: EmployeeSummaryResponseDTO): string {
  if (!employee.journey_started) return "NOT_STARTED";
  if (employee.tasks_total > 0 && employee.tasks_done === employee.tasks_total) return "DONE";
  return employee.current_status ?? "READY";
}

function matchesFilter(status: string, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "attn") return status === "BLOCKED";
  if (filter === "wait") return status === "WAITING_EXTERNAL";
  return status === "READY" || status === "IN_PROGRESS" || status === "DONE";
}

/** "Nhân viên" thật — cổng đúng bảng của prototype v15 (avatar/tiến độ/task hiện tại/trạng thái),
 * dữ liệu từ GET /portal/employees (dùng lại users/team_members/employee_journeys có sẵn). */
export function EmployeesPage() {
  const t = useTranslations("portalEmployees");

  const [employees, setEmployees] = useState<EmployeeSummaryResponseDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    portalHrApi
      .listEmployees()
      .then((result) => setEmployees(result))
      .catch((caught: unknown) => setError(errorMessage(t, caught)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (employees ?? []).filter((e) => {
      const status = statusOf(e);
      return (!q || e.display_name.toLowerCase().includes(q)) && matchesFilter(status, filter);
    });
  }, [employees, query, filter]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const rows = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  return (
    <div className={styles.page}>
      <header className={styles.pagehead}>
        <span className={styles.phi}>
          <Users aria-hidden="true" size={22} />
        </span>
        <div className={styles.pageheadText}>
          <h1>{t("title")}</h1>
          <p>{t("description")}</p>
        </div>
      </header>

      {error ? <p className={styles.banner}>{error}</p> : null}

      <div className={styles.card}>
        <div className={styles.tbar}>
          <div className={styles.search}>
            <Search aria-hidden="true" size={14} />
            <input onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }} placeholder={t("searchPlaceholder")} value={query} />
          </div>
          <div className={styles.chips}>
            {(["all", "attn", "wait", "ok"] as const).map((key) => (
              <button
                className={`${styles.chip} ${filter === key ? styles.chipOn : ""}`}
                key={key}
                onClick={() => {
                  setFilter(key);
                  setPage(1);
                }}
                type="button"
              >
                {t(`filters.${key}`)}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.tableWrap} style={{ minHeight: PAGE_SIZE * 73 + 41 }}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>{t("table.employee")}</th>
                <th>{t("table.stage")}</th>
                <th>{t("table.progress")}</th>
                <th>{t("table.currentTask")}</th>
                <th>{t("table.status")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {employees === null ? (
                <tr>
                  <td colSpan={6}>{t("loading")}</td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6}>{t("empty")}</td>
                </tr>
              ) : (
                rows.map((employee) => {
                  const status = statusOf(employee);
                  const pct = employee.tasks_total > 0 ? Math.round((employee.tasks_done / employee.tasks_total) * 100) : 0;
                  return (
                    <tr key={employee.id}>
                      <td>
                        <div className={styles.cellrow}>
                          <PersonAvatar name={employee.display_name} sizePx={32} />
                          <div>
                            <b>{employee.display_name}</b>
                            <div className={styles.faint}>{employee.email}</div>
                          </div>
                        </div>
                      </td>
                      <td>{employee.current_stage_title ?? "—"}</td>
                      <td>
                        <div className={styles.meter}>
                          <i style={{ width: `${pct}%`, background: status === "BLOCKED" ? "#e05252" : "#3d8fe8" }} />
                        </div>
                        <span className={styles.faint}>{pct}%</span>
                      </td>
                      <td>
                        {employee.current_task_title ?? t("noCurrentTask")}
                      </td>
                      <td>
                        <span className={styles.pill} data-status={status}>
                          {t(`status.${status}`)}
                        </span>
                      </td>
                      <td>
                        <div className={styles.rowActions}>
                          <Link className={styles.btnSm} href="/admin/tasks">
                            <Eye aria-hidden="true" size={13} /> {t("viewTask")}
                          </Link>
                          <button className={styles.btnSm} disabled title={t("soon")} type="button">
                            <Mail aria-hidden="true" size={13} /> {t("nudge")}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        <div className={styles.pager}>
          <span className={styles.faint}>{t("count", { count: filtered.length })}</span>
          {pageCount > 1 ? (
            <div className={styles.pagerButtons}>
              {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
                <button className={n === current ? styles.pagerOn : ""} key={n} onClick={() => setPage(n)} type="button">
                  {n}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
