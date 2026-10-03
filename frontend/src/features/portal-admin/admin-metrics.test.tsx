import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { portalAdminApi } from "@/features/portal-admin/api";
import type { AdminMetricsResponseDTO } from "@/features/portal-admin/dto/responseDTO/admin.response";

import { AdminMetricsPage } from "./AdminMetricsPage";

vi.mock("@/features/portal-admin/api", () => ({ portalAdminApi: { getMetrics: vi.fn() } }));

const t = viMessages.portalAdmin.metrics;

const REPORT: AdminMetricsResponseDTO = {
  days: 7,
  since: "2026-09-24T00:00:00Z",
  calls: 20,
  errors: 2,
  cost_usd: 0.02891,
  operations: [
    {
      operation: "task.proposal",
      kind: "llm",
      calls: 1,
      errors: 0,
      avg_latency_ms: 47484,
      p50_latency_ms: 47484,
      p95_latency_ms: 47484,
      prompt_tokens: 2571,
      completion_tokens: 14901,
      input_count: 0,
      cost_usd: 0.01865,
    },
    {
      operation: "chat.embed",
      kind: "embedding",
      calls: 3,
      errors: 0,
      avg_latency_ms: 1600,
      p50_latency_ms: 1619,
      p95_latency_ms: 1751,
      prompt_tokens: 0,
      completion_tokens: 0,
      input_count: 3,
      cost_usd: 0,
    },
    {
      operation: "custom.operation",
      kind: "llm",
      calls: 2,
      errors: 2,
      avg_latency_ms: 300,
      p50_latency_ms: 300,
      p95_latency_ms: 300,
      prompt_tokens: 10,
      completion_tokens: 1,
      input_count: 0,
      cost_usd: 0.00001,
    },
  ],
  daily: [{ day: "2026-10-01", calls: 20, cost_usd: 0.02891 }],
};

function renderPage() {
  render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <AdminMetricsPage />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(portalAdminApi.getMetrics).mockResolvedValue(REPORT);
});

describe("Chi phí và hiệu năng AI (Admin)", () => {
  it("hiện tổng quan và số liệu theo từng thao tác với tên dễ hiểu, độ trễ đổi sang giây", async () => {
    renderPage();

    expect(await screen.findByText(t.operations.task_proposal)).toBeInTheDocument();
    expect(portalAdminApi.getMetrics).toHaveBeenCalledWith(7);
    expect(screen.getByText("0.029 USD")).toBeInTheDocument();
    expect(screen.getByText("10% số lượt")).toBeInTheDocument(); // 2 lỗi / 20 lượt

    const row = screen.getByText(t.operations.task_proposal).closest("tr") as HTMLElement;
    expect(within(row).getAllByText("47.5 s")).toHaveLength(2); // p50 và p95
    expect(within(row).getByText("14.901")).toBeInTheDocument(); // token ra, định dạng vi-VN
    expect(within(row).getByText("0.019")).toBeInTheDocument();

    const embed = screen.getByText(t.operations.chat_embed).closest("tr") as HTMLElement;
    expect(within(embed).getByText("1.6 s")).toBeInTheDocument();
    expect(screen.getAllByText("custom.operation").length).toBeGreaterThan(0); // thao tác lạ hiện nguyên mã
  });

  it("đổi khoảng thời gian thì tải lại đúng số ngày", async () => {
    renderPage();
    await screen.findByText(t.operations.task_proposal);

    fireEvent.change(screen.getByLabelText(t.period), { target: { value: "30" } });

    await waitFor(() => expect(portalAdminApi.getMetrics).toHaveBeenLastCalledWith(30));
  });

  it("chưa có lượt gọi nào thì báo rõ", async () => {
    vi.mocked(portalAdminApi.getMetrics).mockResolvedValue({ ...REPORT, calls: 0, errors: 0, cost_usd: 0, operations: [], daily: [] });
    renderPage();

    expect(await screen.findByText(t.empty)).toBeInTheDocument();
  });

  it("lỗi tải thì hiện thông báo", async () => {
    const { PortalError } = await vi.importActual<typeof import("@/features/portal-hr/api")>("@/features/portal-hr/api");
    vi.mocked(portalAdminApi.getMetrics).mockRejectedValue(new PortalError("forbidden"));
    renderPage();

    expect(await screen.findByText(viMessages.portalAdmin.errors.forbidden)).toBeInTheDocument();
  });
});
