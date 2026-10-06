"use client";

import { Activity, AlertTriangle, Coins, Gauge } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { portalAdminApi } from "@/features/portal-admin/api";
import type { AdminMetricsResponseDTO } from "@/features/portal-admin/dto/responseDTO/admin.response";

import { adminErrorMessage, adminStyles as s, Kpi, PageHead } from "./adminUi";

const PERIODS = [7, 30, 90] as const;
// Tên thao tác đã được đo (`llm_calls.operation`); thao tác lạ hiện nguyên mã. Khóa dịch đổi "." thành "_" vì next-intl
// hiểu dấu chấm là cấp lồng nhau.
const KNOWN_OPERATIONS = new Set([
  "chat.rewrite",
  "chat.embed",
  "chat.answer",
  "viga.route",
  "ingest.embed",
  "ingest.reembed",
  "ingest.probe",
  "embed.keepwarm",
  "ingest.structure",
  "task.proposal",
]);

function formatMs(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${Math.round(value)} ms`;
}

function formatUsd(value: number): string {
  return value === 0 ? "0" : value < 0.01 ? value.toFixed(5) : value.toFixed(3);
}

/**
 * "Chi phí và hiệu năng AI" (mục 12): số lượt, lỗi, độ trễ p50/p95, token và chi phí ước tính theo từng thao tác, đọc từ
 * `llm_calls`. Chỉ có số liệu, không có nội dung câu hỏi hay tài liệu (INV8). Đơn giá cấu hình ở backend (DeepSeek đã tra
 * ngày 01/10/2026; Modal chưa có giá nên chi phí embedding hiện 0).
 */
export function AdminMetricsPage() {
  const t = useTranslations("portalAdmin");
  const [days, setDays] = useState<number>(7);
  const [report, setReport] = useState<AdminMetricsResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    portalAdminApi
      .getMetrics(days)
      .then((result) => {
        if (cancelled) return;
        setReport(result);
        setError(null);
      })
      .catch((caught: unknown) => !cancelled && setError(adminErrorMessage(t, caught)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const errorRate = report && report.calls > 0 ? Math.round((100 * report.errors) / report.calls) : 0;

  return (
    <div className={s.page}>
      <PageHead
        actions={
          <select aria-label={t("metrics.period")} onChange={(event) => setDays(Number(event.target.value))} value={days}>
            {PERIODS.map((value) => (
              <option key={value} value={value}>
                {t("metrics.lastDays", { count: value })}
              </option>
            ))}
          </select>
        }
        description={t("metrics.description")}
        icon={Gauge}
        title={t("metrics.title")}
        tone="Indigo"
      />
      {error ? <p className={s.banner}>{error}</p> : null}

      <div className={s.kpiGrid}>
        <Kpi icon={Activity} label={t("metrics.kpi.calls")} tone="Blue" value={report?.calls ?? "…"} />
        <Kpi
          icon={AlertTriangle}
          label={t("metrics.kpi.errors")}
          sub={report ? t("metrics.kpi.errorRate", { percent: errorRate }) : undefined}
          tone="Rose"
          value={report?.errors ?? "…"}
        />
        <Kpi
          icon={Coins}
          label={t("metrics.kpi.cost")}
          sub={t("metrics.kpi.costNote")}
          tone="Amber"
          value={report ? `${formatUsd(report.cost_usd)} USD` : "…"}
        />
      </div>

      <div className={s.card}>
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("metrics.table.operation")}</th>
                <th>{t("metrics.table.calls")}</th>
                <th>{t("metrics.table.errors")}</th>
                <th>p50</th>
                <th>p95</th>
                <th>{t("metrics.table.tokensIn")}</th>
                <th>{t("metrics.table.tokensOut")}</th>
                <th>{t("metrics.table.embedded")}</th>
                <th>{t("metrics.table.cost")}</th>
              </tr>
            </thead>
            <tbody>
              {report === null ? (
                <tr>
                  <td className={s.emptyCell} colSpan={9}>
                    {t("common.loading")}
                  </td>
                </tr>
              ) : report.operations.length === 0 ? (
                <tr>
                  <td className={s.emptyCell} colSpan={9}>
                    {t("metrics.empty")}
                  </td>
                </tr>
              ) : (
                report.operations.map((row) => (
                  <tr key={`${row.operation}-${row.kind}`}>
                    <td>
                      <b>{KNOWN_OPERATIONS.has(row.operation) ? t(`metrics.operations.${row.operation.replace(".", "_")}`) : row.operation}</b>
                      <br />
                      <small className={s.faint}>{row.operation}</small>
                    </td>
                    <td>{row.calls}</td>
                    <td>{row.errors}</td>
                    <td>{formatMs(row.p50_latency_ms)}</td>
                    <td>{formatMs(row.p95_latency_ms)}</td>
                    <td>{row.prompt_tokens.toLocaleString("vi-VN")}</td>
                    <td>{row.completion_tokens.toLocaleString("vi-VN")}</td>
                    <td>{row.input_count.toLocaleString("vi-VN")}</td>
                    <td>{formatUsd(row.cost_usd)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <p className={`${s.faint} ${s.cardNote}`}>{t("metrics.note")}</p>
      </div>
    </div>
  );
}
