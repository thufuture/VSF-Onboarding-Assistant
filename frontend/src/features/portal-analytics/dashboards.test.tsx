import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { analyticsApi } from "@/features/portal-analytics/api";
import type { PortalAnalyticsResponseDTO } from "@/features/portal-analytics/dto/responseDTO/analytics.response";
import { AdminDashboardPage } from "@/features/portal-admin/AdminDashboardPage";
import { portalAdminApi } from "@/features/portal-admin/api";
import { HrDashboardPage } from "@/features/portal-hr/HrDashboardPage";
import { portalHrApi } from "@/features/portal-hr/api";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...rest }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href}`} {...rest}>
      {children}
    </a>
  ),
  usePathname: () => "/admin",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/features/portal-analytics/api", () => ({ analyticsApi: { getAnalytics: vi.fn() } }));
vi.mock("@/features/portal-hr/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/portal-hr/api")>()),
  portalHrApi: { getDashboard: vi.fn() },
}));
vi.mock("@/features/portal-admin/api", () => ({ portalAdminApi: { getDashboard: vi.fn() } }));

const EMPTY: PortalAnalyticsResponseDTO = {
  days: 14,
  dates: ["2026-09-30", "2026-10-01"],
  scope: "TEAM",
  team_name: "Kỹ thuật",
  generated_at: "2026-10-01T13:30:00Z",
  people: {
    employees_total: 0,
    completion_percent: 0,
    by_progress: [],
    tasks_by_state: [],
    tasks_by_group: [],
    completed_per_day: [0, 0],
  },
  documents: { total: 0, by_state: [], by_category: [] },
  viga: {
    total_questions: 0,
    questions_per_day: [0, 0],
    by_outcome: [],
    by_route: [],
    no_llm_percent: 0,
    answered_percent: 0,
  },
  tickets: { by_status: [], created_per_day: [0, 0], open_gaps: 0, avg_first_reply_hours: null },
  ai: {
    calls: 0,
    errors: 0,
    cost_usd: 0,
    calls_per_day: [0, 0],
    errors_per_day: [0, 0],
    cost_per_day: [0, 0],
    by_operation: [],
    task_runs: [],
    activation_runs: [],
  },
};

function session(role: SessionUserResponseDTO["role"]): SessionUserResponseDTO {
  return {
    id: 1,
    email: "a@vsf-demo.example",
    display_name: "Người dùng thử",
    role,
    department: null,
    expires_at: "2026-10-02T10:00:00Z",
  };
}

function renderPage(role: SessionUserResponseDTO["role"], page: ReactNode) {
  render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider initialUser={session(role)}>{page}</SessionProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(analyticsApi.getAnalytics).mockResolvedValue(EMPTY);
});

describe("Trang Tổng quan có số liệu theo thời gian", () => {
  it("HR: giữ bốn chỉ số lộ trình và thêm các biểu đồ trong phạm vi phòng ban", async () => {
    vi.mocked(portalHrApi.getDashboard).mockResolvedValue({
      journey_template_count: 1,
      journey_stage_count: 5,
      task_template_count: 21,
      document_count: 4,
    });
    renderPage("HR", <HrDashboardPage />);

    expect(await screen.findByText("Phòng ban: Kỹ thuật")).toBeInTheDocument();
    expect(screen.getByText("21")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Số liệu theo thời gian" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hoạt động mỗi ngày" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Chi phí AI mỗi ngày" })).toBeInTheDocument();
  });

  it("Admin: giữ KPI quản trị và thêm số liệu toàn hệ thống", async () => {
    vi.mocked(portalAdminApi.getDashboard).mockResolvedValue({
      active_teams: 3,
      archived_teams: 0,
      hr_count: 2,
      employee_count: 9,
      employees_without_team: 0,
      inactive_users: 0,
      employees_by_team: [["Kỹ thuật", 9]],
      recent_logs: [],
    });
    vi.mocked(analyticsApi.getAnalytics).mockResolvedValue({ ...EMPTY, scope: "ALL", team_name: null });
    renderPage("ADMIN", <AdminDashboardPage />);

    expect(await screen.findByText("Toàn hệ thống")).toBeInTheDocument();
    expect(await screen.findByText("Kỹ thuật")).toBeInTheDocument(); // biểu đồ nhân viên theo phòng ban cũ vẫn còn
    expect(screen.getByRole("heading", { name: "Chi phí AI mỗi ngày" })).toBeInTheDocument();
  });
});
