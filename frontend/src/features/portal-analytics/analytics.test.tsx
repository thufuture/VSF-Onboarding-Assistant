import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { analyticsApi } from "@/features/portal-analytics/api";
import type { PortalAnalyticsResponseDTO } from "@/features/portal-analytics/dto/responseDTO/analytics.response";
import { PortalError } from "@/features/portal-hr/api";

import { AnalyticsPanel } from "./AnalyticsPanel";

vi.mock("@/features/portal-analytics/api", () => ({ analyticsApi: { getAnalytics: vi.fn() } }));

const DATES = ["2026-09-25", "2026-09-26", "2026-09-27", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"];

function run(
  id: number,
  overrides: Partial<PortalAnalyticsResponseDTO["ai"]["task_runs"][number]> = {},
): PortalAnalyticsResponseDTO["ai"]["task_runs"][number] {
  return {
    job_id: id,
    started_at: "2026-10-01T13:00:00Z",
    status: "SUCCEEDED",
    duration_seconds: 48.2,
    documents: 2,
    items: 14,
    llm_calls: 2,
    llm_latency_ms: 47484,
    prompt_tokens: 2571,
    completion_tokens: 14901,
    cost_usd: 0.01865,
    ...overrides,
  };
}

function report(overrides: Partial<PortalAnalyticsResponseDTO> = {}): PortalAnalyticsResponseDTO {
  return {
    days: 7,
    dates: DATES,
    scope: "TEAM",
    team_name: "Kỹ thuật",
    generated_at: "2026-10-01T13:30:00Z",
    people: {
      employees_total: 12,
      completion_percent: 38,
      by_progress: [
        { key: "NO_JOURNEY", count: 1 },
        { key: "NOT_STARTED", count: 3 },
        { key: "IN_PROGRESS", count: 7 },
        { key: "COMPLETED", count: 1 },
      ],
      tasks_by_state: [
        { key: "done", count: 30 },
        { key: "ready", count: 20 },
        { key: "locked", count: 28 },
      ],
      tasks_by_group: [
        { group: "TRAINING", done: 10, ready: 5, locked: 3 },
        { group: "NONE", done: 20, ready: 15, locked: 25 },
      ],
      completed_per_day: [0, 2, 1, 0, 5, 3, 4],
    },
    documents: {
      total: 4,
      by_state: [
        { key: "CURRENT", count: 3 },
        { key: "SCHEDULED", count: 0 },
        { key: "DRAFT", count: 1 },
        { key: "PROCESSING", count: 0 },
        { key: "SUPERSEDED", count: 0 },
        { key: "FAILED", count: 0 },
      ],
      by_category: [
        { key: "Đào tạo", count: 3 },
        { key: "Thiết bị", count: 1 },
      ],
    },
    viga: {
      total_questions: 40,
      questions_per_day: [1, 3, 2, 4, 10, 12, 8],
      by_outcome: [
        { key: "ANSWER", count: 10 },
        { key: "DAY_PLAN", count: 12 },
        { key: "NEXT_STEP", count: 6 },
        { key: "NO_BASIS", count: 7 },
        { key: "OUT_OF_SCOPE", count: 5 },
        { key: "ERROR", count: 0 },
      ],
      by_route: [
        { key: "SHORTCUT", count: 18 },
        { key: "GUARD", count: 5 },
        { key: "LLM", count: 17 },
        { key: "FALLBACK", count: 0 },
      ],
      no_llm_percent: 58,
      answered_percent: 70,
    },
    tickets: {
      by_status: [
        { key: "OPEN", count: 2 },
        { key: "IN_PROGRESS", count: 1 },
        { key: "RESOLVED", count: 4 },
        { key: "CLOSED", count: 0 },
      ],
      created_per_day: [0, 1, 0, 2, 1, 1, 2],
      open_gaps: 3,
      avg_first_reply_hours: 4.5,
    },
    ai: {
      calls: 55,
      errors: 2,
      cost_usd: 0.0289,
      calls_per_day: [0, 5, 3, 8, 12, 15, 12],
      errors_per_day: [0, 0, 0, 1, 0, 1, 0],
      cost_per_day: [0, 0.001, 0.002, 0.005, 0.006, 0.0089, 0.006],
      by_operation: [
        {
          operation: "task.proposal",
          kind: "llm",
          calls: 3,
          errors: 0,
          p50_latency_ms: 47484,
          p95_latency_ms: 50000,
          prompt_tokens: 2571,
          completion_tokens: 14901,
          input_count: 0,
          cost_usd: 0.01865,
        },
        {
          operation: "chat.answer",
          kind: "llm",
          calls: 10,
          errors: 1,
          p50_latency_ms: 6800,
          p95_latency_ms: 8100,
          prompt_tokens: 6800,
          completion_tokens: 290,
          input_count: 0,
          cost_usd: 0.0033,
        },
        {
          operation: "custom.operation",
          kind: "llm",
          calls: 1,
          errors: 0,
          p50_latency_ms: 300,
          p95_latency_ms: 300,
          prompt_tokens: 1,
          completion_tokens: 1,
          input_count: 0,
          cost_usd: 0.0001,
        },
      ],
      task_runs: [
        run(11, { started_at: "2026-09-30T08:00:00Z", duration_seconds: 52.4, items: 12, cost_usd: 0.0201 }),
        run(12),
        run(13, { status: "FAILED", duration_seconds: 3.1, items: 0, llm_calls: 0, llm_latency_ms: 0, cost_usd: 0 }),
      ],
      activation_runs: [
        run(21, { duration_seconds: 4.7, items: 18, llm_calls: 1, llm_latency_ms: 3300, cost_usd: 0 }),
      ],
    },
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <AnalyticsPanel />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(analyticsApi.getAnalytics).mockResolvedValue(report());
});

describe("Số liệu theo thời gian (trang Tổng quan)", () => {
  it("hiện phạm vi phòng ban và tải đúng 14 ngày mặc định, không có thẻ chỉ số hay tiêu đề mục thừa", async () => {
    renderPanel();

    expect(await screen.findByText("Phòng ban: Kỹ thuật")).toBeInTheDocument();
    expect(analyticsApi.getAnalytics).toHaveBeenCalledWith(14);
    // Mỗi biểu đồ đã có tên, nên chỉ còn một tiêu đề cấp 2 (thanh công cụ) và không còn thẻ chỉ số.
    expect(screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "Số liệu theo thời gian",
    ]);
    for (const removed of ["Nhân viên và Viga", "Chi phí và độ trễ AI", "Ticket đang mở", "Câu hỏi Viga"]) {
      expect(screen.queryByText(removed, { selector: "h2, small" })).not.toBeInTheDocument();
    }
    expect(screen.queryByText("38% task đã hoàn thành")).not.toBeInTheDocument();
  });

  it("Admin thấy nhãn toàn hệ thống; HR chưa có phòng ban thấy thông báo thay vì tên phòng", async () => {
    vi.mocked(analyticsApi.getAnalytics).mockResolvedValueOnce(report({ scope: "ALL", team_name: null }));
    const { unmount } = renderPanel();
    expect(await screen.findByText("Toàn hệ thống")).toBeInTheDocument();
    unmount();

    vi.mocked(analyticsApi.getAnalytics).mockResolvedValueOnce(report({ scope: "TEAM", team_name: null }));
    renderPanel();
    expect(await screen.findByText("Chưa thuộc phòng ban nào")).toBeInTheDocument();
  });

  it("biểu đồ tròn có chú thích đủ số và tỷ lệ", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    const progress = screen.getByRole("heading", { name: "Tiến độ nhân viên" }).closest("section")!;
    expect(within(progress).getByText("Đang làm").closest("li")).toHaveTextContent("758%");
    expect(within(progress).getByText("Chưa có lộ trình")).toBeInTheDocument();
  });

  it("chi phí theo thao tác: thao tác lạ gộp vào Khác, thao tác không tốn tiền không hiện", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    const cost = screen.getByRole("heading", { name: "Chi phí theo thao tác" }).closest("section")!;
    expect(within(cost).getByText("Tạo task bằng AI")).toBeInTheDocument();
    expect(within(cost).getByText("Khác")).toBeInTheDocument();
    expect(within(cost).queryByText("custom.operation")).not.toBeInTheDocument();
  });

  it("độ trễ và chi phí mỗi lượt tạo task: một cột mỗi lượt, chú giải có đủ chi tiết, trung bình chỉ tính lượt thành công", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    expect(
      screen.getByText("Trung bình 2 lượt thành công gần nhất: 50.3 s mỗi lượt, 0.019 USD, 13 đề xuất."),
    ).toBeInTheDocument();

    const latency = screen.getByRole("heading", { name: "Độ trễ mỗi lượt tạo task" }).closest("section")!;
    const plot = within(latency).getByRole("group", { name: "Độ trễ mỗi lượt tạo task" });
    fireEvent.keyDown(plot, { key: "ArrowRight" }); // lượt đầu
    fireEvent.keyDown(plot, { key: "ArrowRight" }); // lượt thứ hai (#12)
    const tip = within(within(latency).getByRole("status"));
    expect(tip.getByText(/Lượt #12/)).toBeInTheDocument();
    expect(tip.getByText("Thời gian chạy")).toBeInTheDocument();
    expect(tip.getByText("48.2 s")).toBeInTheDocument();
    expect(tip.getByText("Chờ mô hình AI")).toBeInTheDocument();
    expect(tip.getByText("47.5 s")).toBeInTheDocument();
    expect(tip.getByText("Số đề xuất")).toBeInTheDocument();
    expect(tip.getByText("14")).toBeInTheDocument();
    expect(tip.getByText("14.901")).toBeInTheDocument();

    const costCard = screen.getByRole("heading", { name: "Chi phí mỗi lượt tạo task" }).closest("section")!;
    fireEvent.keyDown(within(costCard).getByRole("group", { name: "Chi phí mỗi lượt tạo task" }), { key: "ArrowRight" });
    expect(within(within(costCard).getByRole("status")).getByText("0.020 USD")).toBeInTheDocument();
  });

  it("bảng số liệu của từng lượt: trạng thái lỗi, thời gian, token và chi phí", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    const card = screen.getByRole("heading", { name: "Độ trễ mỗi lượt tạo task" }).closest("section")!;
    fireEvent.click(within(card).getByRole("button", { name: /Xem dạng bảng/ }));
    const table = within(within(card).getByRole("table"));
    expect(table.getAllByRole("row")).toHaveLength(4); // tiêu đề + 3 lượt
    const failed = table.getByText(/#13/).closest("tr")!;
    expect(failed).toHaveTextContent("Lỗi");
    expect(failed).toHaveTextContent("3.10 s");
  });

  it("chỉ giữ sáu biểu đồ quan trọng, không còn các thẻ phụ", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    const titles = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(titles).toEqual([
      "Tiến độ nhân viên",
      "Hoạt động mỗi ngày",
      "Chi phí AI mỗi ngày",
      "Chi phí theo thao tác",
      "Độ trễ mỗi lượt tạo task",
      "Chi phí mỗi lượt tạo task",
    ]);
    for (const removed of ["Kết quả câu trả lời của Viga", "Từng lượt tạo task bằng AI", "Trạng thái task", "Task theo nhóm", "Ticket theo trạng thái", "Phiên bản tài liệu", "Độ trễ theo thao tác"]) {
      expect(screen.queryByRole("heading", { name: removed })).not.toBeInTheDocument();
    }
  });

  it("biểu đồ hoạt động gộp task hoàn thành, câu hỏi Viga và ticket mới trên một trục", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    const card = screen.getByRole("heading", { name: "Hoạt động mỗi ngày" }).closest("section")!;
    const plot = within(card).getByRole("group", { name: "Hoạt động mỗi ngày" });
    fireEvent.keyDown(plot, { key: "ArrowRight" }); // 25/09
    fireEvent.keyDown(plot, { key: "ArrowRight" }); // 26/09
    const tip = within(within(card).getByRole("status"));
    expect(tip.getByText("Task hoàn thành")).toBeInTheDocument();
    expect(tip.getByText("Câu hỏi Viga")).toBeInTheDocument();
    expect(tip.getByText("Ticket mới")).toBeInTheDocument();
    expect(tip.getByText("2")).toBeInTheDocument(); // task xong ngày 26/09
    expect(tip.getByText("3")).toBeInTheDocument(); // câu hỏi Viga ngày 26/09
  });

  it("chưa có lượt nào thì nói rõ thay vì vẽ biểu đồ trống", async () => {
    const base = report();
    vi.mocked(analyticsApi.getAnalytics).mockResolvedValue({
      ...base,
      ai: { ...base.ai, task_runs: [] },
    });
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");

    // Hai thẻ theo từng lượt vẫn có, mỗi thẻ ghi rõ chưa có lượt nào thay vì vẽ biểu đồ trống.
    expect(screen.getAllByText("Chưa có lượt tạo task nào gần đây.")).toHaveLength(2);
    expect(screen.queryByRole("group", { name: "Độ trễ mỗi lượt tạo task" })).not.toBeInTheDocument();
  });

  it("đổi khoảng thời gian thì tải lại đúng số ngày và không lặp lại việc tải khi vẽ lại", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");
    expect(analyticsApi.getAnalytics).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByLabelText("Khoảng thời gian"), { target: { value: "30" } });
    await waitFor(() => expect(analyticsApi.getAnalytics).toHaveBeenLastCalledWith(30));
    expect(analyticsApi.getAnalytics).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getAllByRole("button", { name: /Xem dạng bảng/ })[0]!); // vẽ lại không gọi lại API
    expect(analyticsApi.getAnalytics).toHaveBeenCalledTimes(2);
  });

  it("không có quyền hoặc lỗi mạng thì hiện thông báo đúng loại", async () => {
    vi.mocked(analyticsApi.getAnalytics).mockRejectedValueOnce(new PortalError("forbidden"));
    const { unmount } = renderPanel();
    expect(await screen.findByText("Bạn không có quyền xem số liệu này.")).toBeInTheDocument();
    unmount();

    vi.mocked(analyticsApi.getAnalytics).mockRejectedValueOnce(new Error("boom"));
    renderPanel();
    expect(await screen.findByText("Chưa tải được số liệu. Hãy thử lại sau.")).toBeInTheDocument();
  });

  it("mỗi biểu đồ trong số sáu biểu đồ đều có nút xem dạng bảng", async () => {
    renderPanel();
    await screen.findByText("Phòng ban: Kỹ thuật");
    expect(screen.getAllByRole("button", { name: /Xem dạng bảng/ })).toHaveLength(6);
  });
});
