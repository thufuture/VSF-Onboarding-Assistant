"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { BarChart, type BarCategory } from "@/components/charts/BarChart";
import { ChartCard, type ChartTable } from "@/components/charts/ChartCard";
import { DonutChart, type DonutSlice } from "@/components/charts/DonutChart";
import { LineChart } from "@/components/charts/LineChart";
import type { ChartSeries, TooltipRow } from "@/components/charts/chartTheme";
import { analyticsApi } from "@/features/portal-analytics/api";
import type {
  JobRunResponseDTO,
  PortalAnalyticsResponseDTO,
} from "@/features/portal-analytics/dto/responseDTO/analytics.response";
import { PortalError } from "@/features/portal-hr/api";

import {
  dayLabel,
  dayTitle,
  formatCount,
  formatMs,
  formatSeconds,
  formatUsd,
  formatUsdAxis,
  KNOWN_OPERATIONS,
  OPERATION_SLOT,
  PROGRESS_SLOT,
  runLabel,
} from "./analyticsFormat";
import styles from "./AnalyticsPanel.module.scss";

const PERIODS = [7, 14, 30] as const;

function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

/** Bảng số liệu cho biểu đồ theo ngày: cột đầu là nhãn, mỗi chuỗi một cột. */
function seriesTable(
  firstHead: string,
  labels: string[],
  series: ChartSeries[],
  format: (value: number) => string,
): ChartTable {
  return {
    head: [firstHead, ...series.map((item) => item.label)],
    rows: labels.map((label, index) => [label, ...series.map((item) => format(item.values[index] ?? 0))]),
  };
}

function sliceTable(head: [string, string], slices: DonutSlice[], format: (value: number) => string): ChartTable {
  const total = sum(slices.map((slice) => slice.value));
  return {
    head: [head[0], head[1], "%"],
    rows: slices.map((slice) => [
      slice.label,
      format(slice.value),
      `${total > 0 ? Math.round((100 * slice.value) / total) : 0}%`,
    ]),
  };
}

/**
 * Số liệu theo thời gian cho trang Tổng quan của HR (phòng ban của mình) và Admin (toàn hệ thống): bảy biểu đồ quan trọng nhất
 * (tiến độ nhân viên, kết quả trả lời của Viga, hoạt động mỗi ngày, chi phí AI mỗi ngày và theo thao tác, độ trễ và chi phí của
 * từng lượt tạo task), mỗi biểu đồ tự có tên nên không thêm thẻ chỉ số hay tiêu đề mục. Chỉ số liệu tổng hợp từ
 * `GET /portal/analytics` (API còn trả nhiều hơn thế, giao diện chỉ chọn phần cần xem), không có nội dung câu hỏi hay tài liệu.
 */
export function AnalyticsPanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const [days, setDays] = useState<number>(14);
  const [data, setData] = useState<PortalAnalyticsResponseDTO | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    analyticsApi
      .getAnalytics(days)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setErrorKey(null);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setErrorKey(caught instanceof PortalError ? caught.code : "unavailable");
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  const toolbar = (
    <div className={styles.toolbar}>
      <div>
        <h2>{t("title")}</h2>
        <p>
          {data
            ? t("updatedAt", {
                time: new Date(data.generated_at).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" }),
              })
            : t("loading")}
        </p>
      </div>
      {data ? (
        <span className={styles.scope}>
          {data.scope === "ALL"
            ? t("scopeAll")
            : data.team_name
              ? t("scopeTeam", { team: data.team_name })
              : t("scopeNoTeam")}
        </span>
      ) : null}
      <select aria-label={t("period")} onChange={(event) => setDays(Number(event.target.value))} value={days}>
        {PERIODS.map((value) => (
          <option key={value} value={value}>
            {t("lastDays", { count: value })}
          </option>
        ))}
      </select>
    </div>
  );

  if (errorKey !== null && data === null) {
    return (
      <div className={styles.panel}>
        {toolbar}
        <p className={styles.banner}>{t(`errors.${errorKey}`)}</p>
      </div>
    );
  }
  if (data === null) {
    return (
      <div aria-busy="true" className={styles.panel}>
        {toolbar}
      </div>
    );
  }

  const { people, viga, tickets, ai } = data;
  const labels = data.dates.map(dayLabel);
  const titles = data.dates.map((iso) => dayTitle(iso, locale));
  const dateHead = t("table.date");
  const stateHead = t("table.state");
  const countHead = t("table.count");

  const operationName = (operation: string) =>
    KNOWN_OPERATIONS.has(operation) ? t(`operations.${operation.replace(".", "_")}`) : operation;

  // ── nhân viên và Viga ──
  const progressSlices: DonutSlice[] = people.by_progress.map((item) => ({
    key: item.key,
    label: t(`progress.states.${item.key}`),
    value: item.count,
    slot: PROGRESS_SLOT[item.key] ?? "muted",
  }));
  const activitySeries: ChartSeries[] = [
    { key: "completed", label: t("activity.completed"), slot: 3, values: people.completed_per_day },
    { key: "questions", label: t("activity.questions"), slot: 1, values: viga.questions_per_day },
    { key: "tickets", label: t("activity.tickets"), slot: 2, values: tickets.created_per_day },
  ];

  // ── chi phí AI ──
  const costSeries: ChartSeries[] = [{ key: "cost", label: t("costDay.series"), slot: 4, values: ai.cost_per_day }];
  const topCosts = ai.by_operation.filter((row) => OPERATION_SLOT[row.operation] !== undefined && row.cost_usd > 0);
  const otherCost = sum(
    ai.by_operation.filter((row) => OPERATION_SLOT[row.operation] === undefined).map((row) => row.cost_usd),
  );
  const costSlices: DonutSlice[] = [
    ...topCosts.map((row) => ({
      key: row.operation,
      label: operationName(row.operation),
      value: row.cost_usd,
      slot: OPERATION_SLOT[row.operation] ?? ("muted" as const),
    })),
    ...(otherCost > 0 ? [{ key: "other", label: t("costOp.other"), value: otherCost, slot: "muted" as const }] : []),
  ];

  // ── từng lượt tạo task ──
  // `withCost: false` cho biểu đồ chi phí, nơi chi phí đã là chuỗi chính nên không lặp lại trong dòng thêm.
  const runExtra = (run: JobRunResponseDTO, withCost: boolean): TooltipRow[] => [
    { label: t("runs.status"), value: t(`runs.statuses.${run.status}`) },
    { label: t("runs.documents"), value: formatCount(run.documents) },
    { label: t("runs.proposals"), value: formatCount(run.items) },
    { label: t("runs.llmCalls"), value: formatCount(run.llm_calls) },
    { label: t("runs.tokensIn"), value: formatCount(run.prompt_tokens) },
    { label: t("runs.tokensOut"), value: formatCount(run.completion_tokens) },
    ...(withCost ? [{ label: t("runs.cost"), value: `${formatUsd(run.cost_usd)} USD` }] : []),
  ];
  const runCategories = (withCost: boolean): BarCategory[] =>
    ai.task_runs.map((run) => ({
      key: String(run.job_id),
      label: runLabel(run.started_at),
      title: `${t("runs.run")} #${run.job_id} · ${runLabel(run.started_at)}`,
      extra: runExtra(run, withCost),
    }));
  const latencySeries: ChartSeries[] = [
    {
      key: "duration",
      label: t("runs.duration"),
      slot: 1,
      values: ai.task_runs.map((run) => run.duration_seconds ?? 0),
    },
    { key: "llm", label: t("runs.llmLatency"), slot: 2, values: ai.task_runs.map((run) => run.llm_latency_ms / 1000) },
  ];
  const runCostSeries: ChartSeries[] = [
    { key: "cost", label: t("runs.cost"), slot: 4, values: ai.task_runs.map((run) => run.cost_usd) },
  ];

  const succeeded = ai.task_runs.filter((run) => run.status === "SUCCEEDED");
  const average = (pick: (run: JobRunResponseDTO) => number) =>
    succeeded.length > 0 ? sum(succeeded.map(pick)) / succeeded.length : 0;

  // Số trung bình các lượt thành công nằm ngay trong phụ đề của thẻ (không còn đầu mục riêng).
  const runsSubtitle =
    succeeded.length > 0
      ? t("runs.average", {
          seconds: formatSeconds(average((run) => run.duration_seconds ?? 0)),
          cost: formatUsd(average((run) => run.cost_usd)),
          items: Math.round(average((run) => run.items)),
          count: succeeded.length,
        })
      : t("runs.latencySub");

  const runsTable: ChartTable = {
    head: [
      t("runs.run"),
      t("runs.status"),
      t("runs.duration"),
      t("runs.llmLatency"),
      t("runs.proposals"),
      t("runs.tokensIn"),
      t("runs.tokensOut"),
      t("runs.cost"),
    ],
    rows: ai.task_runs.map((run) => [
      `#${run.job_id} · ${runLabel(run.started_at)}`,
      t(`runs.statuses.${run.status}`),
      run.duration_seconds === null ? "—" : formatSeconds(run.duration_seconds),
      formatMs(run.llm_latency_ms),
      formatCount(run.items),
      formatCount(run.prompt_tokens),
      formatCount(run.completion_tokens),
      formatUsd(run.cost_usd),
    ]),
  };

  return (
    <div aria-busy="false" className={styles.panel}>
      {toolbar}
      {errorKey !== null ? <p className={styles.banner}>{t(`errors.${errorKey}`)}</p> : null}

      <div className={styles.grid}>
        <ChartCard
          subtitle={t("progress.sub")}
          table={sliceTable([stateHead, countHead], progressSlices, String)}
          title={t("progress.title")}
        >
          <DonutChart
            ariaLabel={t("progress.title")}
            centerLabel={t("progress.center")}
            centerValue={String(people.employees_total)}
            slices={progressSlices}
          />
        </ChartCard>
        <ChartCard
          subtitle={t("activity.sub")}
          table={seriesTable(dateHead, labels, activitySeries, String)}
          title={t("activity.title")}
        >
          <LineChart ariaLabel={t("activity.title")} integer labels={labels} series={activitySeries} titles={titles} />
        </ChartCard>
        <ChartCard
          subtitle={t("costDay.sub")}
          table={seriesTable(dateHead, labels, costSeries, formatUsd)}
          title={t("costDay.title")}
        >
          <LineChart
            ariaLabel={t("costDay.title")}
            formatAxis={formatUsdAxis}
            formatValue={formatUsd}
            labels={labels}
            series={costSeries}
            titles={titles}
          />
        </ChartCard>
        <ChartCard
          subtitle={t("costOp.sub")}
          table={sliceTable([t("table.operation"), "USD"], costSlices, formatUsd)}
          title={t("costOp.title")}
        >
          <DonutChart
            ariaLabel={t("costOp.title")}
            centerLabel="USD"
            centerValue={formatUsd(ai.cost_usd)}
            formatValue={formatUsd}
            slices={
              costSlices.length > 0 ? costSlices : [{ key: "none", label: t("costOp.none"), value: 0, slot: "muted" }]
            }
          />
        </ChartCard>

        <ChartCard subtitle={runsSubtitle} table={runsTable} title={t("runs.latencyTitle")}>
          {ai.task_runs.length === 0 ? (
            <p className={styles.empty}>{t("runs.noRuns")}</p>
          ) : (
            <BarChart
              ariaLabel={t("runs.latencyTitle")}
              categories={runCategories(true)}
              formatValue={formatSeconds}
              series={latencySeries}
            />
          )}
        </ChartCard>
        <ChartCard subtitle={t("runs.costSub")} table={runsTable} title={t("runs.costTitle")}>
          {ai.task_runs.length === 0 ? (
            <p className={styles.empty}>{t("runs.noRuns")}</p>
          ) : (
            <BarChart
              ariaLabel={t("runs.costTitle")}
              categories={runCategories(false)}
              formatAxis={formatUsdAxis}
              formatValue={(value) => `${formatUsd(value)} USD`}
              series={runCostSeries}
            />
          )}
        </ChartCard>
      </div>
    </div>
  );
}
