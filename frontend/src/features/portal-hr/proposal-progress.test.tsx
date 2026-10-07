import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { JobResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { portalHrApi } from "@/features/portal-hr/api";

import { AiTasksPage } from "./AiTasksPage";
import { estimateRemainingSeconds, ProposalProgress } from "./ProposalProgress";

vi.mock("@/features/portal-hr/api", () => {
  class PortalError extends Error {
    readonly code: string;
    constructor(code: string) {
      super(code);
      this.code = code;
    }
  }
  return {
    PortalError,
    portalHrApi: {
      listDocuments: vi.fn(),
      listStageOptions: vi.fn(),
      createJourneyTemplate: vi.fn(),
      createJourneyStage: vi.fn(),
      getJob: vi.fn(),
      listActiveJobs: vi.fn(),
      createAiTaskProposalJob: vi.fn(),
      acceptAiTaskProposal: vi.fn(),
    },
  };
});
vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
  usePathname: () => "/admin/ai-tasks",
  useRouter: () => ({ replace: vi.fn() }),
}));

const api = vi.mocked(portalHrApi);
const t = viMessages.portalHr;

function jobOf(overrides: Partial<JobResponseDTO> = {}): JobResponseDTO {
  return {
    id: 500,
    kind: "AI_TASK_PROPOSAL",
    status: "RUNNING",
    progress_percent: 40,
    stage: "AI đang soạn task (30 giây)",
    result: null,
    error: null,
    document_version_id: null,
    created_at: "2026-10-03T00:00:00Z",
    finished_at: null,
    started_at: "2026-10-03T00:00:01Z",
    elapsed_seconds: 30,
    queue_ahead: null,
    progress: {
      version: 1,
      steps: [
        { key: "read", status: "done", done: 1, total: 1, seconds: 0.1 },
        { key: "draft", status: "running", done: 1, total: 3, seconds: 12.4 },
        { key: "verify", status: "pending", done: 0, total: 0, seconds: null },
        { key: "cover", status: "pending", done: 0, total: 0, seconds: null },
        { key: "order", status: "skipped", done: 0, total: 0, seconds: null },
        { key: "save", status: "pending", done: 0, total: 0, seconds: null },
      ],
      documents: [],
    },
    ...overrides,
  };
}

function wrap(node: React.ReactNode) {
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider
        initialUser={{
          id: 1,
          email: "hr@vsf-demo.example",
          display_name: "Phạm Thị Hồng",
          role: "HR",
          department: "HR Onboarding",
          expires_at: "2099-01-01T00:00:00Z",
        }}
      >
        {node}
      </SessionProvider>
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  document.title = "Tạo task bằng AI";
});
afterEach(() => {
  vi.useRealTimers();
});

describe("estimateRemainingSeconds", () => {
  it("chỉ ước lượng khi đã đủ dữ liệu và chưa sắp xong", () => {
    expect(estimateRemainingSeconds(40, 30)).toBe(45); // 30 giây được 40% => còn 60% ≈ 45 giây
    expect(estimateRemainingSeconds(5, 30)).toBeNull(); // quá sớm
    expect(estimateRemainingSeconds(50, 2)).toBeNull(); // chạy chưa tới 3 giây
    expect(estimateRemainingSeconds(99, 60)).toBeNull(); // sắp xong
  });
});

describe("ProposalProgress", () => {
  it("hiện từng bước với trạng thái, số đếm theo lô, giây và thời gian còn lại", () => {
    render(wrap(<ProposalProgress creating={null} job={jobOf()} lost={false} />));

    const box = within(screen.getByTestId("proposal-progress"));
    expect(box.getByText("40%")).toBeInTheDocument();
    const steps = box.getAllByRole("listitem");
    expect(steps.map((li) => li.getAttribute("data-status"))).toEqual([
      "done",
      "running",
      "pending",
      "pending",
      "skipped",
      "pending",
    ]);
    expect(within(steps[1]!).getByText(t.progress.steps.draft)).toBeInTheDocument();
    expect(within(steps[1]!).getByText("1/3")).toBeInTheDocument(); // đã xong 1 trong 3 lô
    expect(within(steps[1]!).getByText("12 giây")).toBeInTheDocument();
    expect(within(steps[4]!).getByText(t.progress.skipped)).toBeInTheDocument();
    expect(box.getByText(/Đã chạy 30 giây/)).toBeInTheDocument();
    expect(box.getByText(/còn khoảng 45 giây/)).toBeInTheDocument();
  });

  it("job còn đang chờ: nói rõ đang xếp hàng và còn mấy việc phía trước, chưa ước lượng thời gian", () => {
    const waiting = jobOf({ status: "PENDING", progress_percent: 0, progress: null, elapsed_seconds: null, queue_ahead: 2 });
    render(wrap(<ProposalProgress creating={null} job={waiting} lost={false} />));

    expect(screen.getByText(t.progress.queued)).toBeInTheDocument();
    expect(screen.getByText("Trước bạn còn 2 việc đang chờ.")).toBeInTheDocument();
    expect(screen.queryByText(/còn khoảng/)).not.toBeInTheDocument();
  });

  it("nhiều tài liệu: liệt kê phần trăm từng tài liệu", () => {
    const job = jobOf();
    job.progress!.documents = [
      { version_id: 1, title: "Hướng dẫn ngày 1", percent: 80, failed: false },
      { version_id: 2, title: "Quy định chung", percent: 10, failed: false },
    ];
    render(wrap(<ProposalProgress creating={null} job={job} lost={false} />));

    expect(screen.getByText("Hướng dẫn ngày 1")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("10%")).toBeInTheDocument();
  });

  it("tên tab hiện phần trăm khi đang chạy và trả lại tên cũ khi xong", () => {
    const { unmount } = render(wrap(<ProposalProgress creating={null} job={jobOf()} lost={false} />));
    expect(document.title).toBe("40% · Tạo task bằng AI");

    unmount();
    expect(document.title).toBe("Tạo task bằng AI");
  });

  it("mất kết nối khi hỏi tiến độ: báo rõ việc vẫn chạy nền", () => {
    render(wrap(<ProposalProgress creating={null} job={jobOf()} lost />));

    expect(screen.getByText(t.progress.lost)).toBeInTheDocument();
  });

  it("đang tạo task thật: hiện đã tạo bao nhiêu trên tổng", () => {
    render(wrap(<ProposalProgress creating={{ done: 3, total: 16 }} job={null} lost={false} />));

    expect(screen.getByText("Đang tạo task 3/16")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "19");
  });

  it("đồng hồ tự chạy mỗi giây dựa trên số giây backend trả về", () => {
    vi.useFakeTimers();
    render(wrap(<ProposalProgress creating={null} job={jobOf({ elapsed_seconds: 10 })} lost={false} />));
    expect(screen.getByText(/Đã chạy 10 giây/)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText(/Đã chạy 13 giây/)).toBeInTheDocument();
  });
});

describe("AiTasksPage: tiếp tục lượt đang chạy khi tải lại trang", () => {
  it("còn job tạo task đang chạy: hiện tiến độ ngay, không bắt chạy lại", async () => {
    api.listDocuments.mockResolvedValue([]);
    api.listStageOptions.mockResolvedValue([
      { id: 70, journey_template_id: 7, title: "Ngày 1", template_title: "Lộ trình onboarding" },
    ]);
    api.listActiveJobs.mockResolvedValue([jobOf()]);
    api.getJob.mockResolvedValue(jobOf());

    render(wrap(<AiTasksPage />));

    expect(await screen.findByTestId("proposal-progress")).toBeInTheDocument();
    expect(api.listActiveJobs).toHaveBeenCalledWith("AI_TASK_PROPOSAL");
    await waitFor(() => expect(api.getJob).toHaveBeenCalledWith(500));
    expect(api.createAiTaskProposalJob).not.toHaveBeenCalled();
  });

  it("không có job nào đang chạy: không hiện khung tiến độ", async () => {
    api.listDocuments.mockResolvedValue([]);
    api.listStageOptions.mockResolvedValue([]);
    api.listActiveJobs.mockResolvedValue([]);

    render(wrap(<AiTasksPage />));

    await waitFor(() => expect(api.listActiveJobs).toHaveBeenCalled());
    expect(screen.queryByTestId("proposal-progress")).not.toBeInTheDocument();
  });

  it("đang tạo task thật: hiện n/tổng cho tới khi xong", async () => {
    const doc = {
      id: 1,
      title: "Hướng dẫn ngày 1",
      category_name: "Onboarding",
      status: "ACTIVE",
      updated_at: "2026-10-01T00:00:00Z",
      latest_version_id: 31,
      section_count: 3,
      source_key: "day1",
      category_slug: "onboarding",
      owner_name: "HR",
      task_titles: [],
      current_version_label: "1.0",
      version_count: 1,
      draft_count: 0,
      processing_count: 0,
      processing_version_ids: [],
    };
    const proposal = (title: string, order: number) => ({
      title,
      summary: "s",
      instructions_markdown: "Bước 1",
      done_criteria: ["Xong"],
      estimated_minutes: 10,
      source_chunks: [{ document_section_id: order, quote: `Trích ${title}`, heading: `Mục ${order}` }],
      confidence: "HIGH" as const,
      warnings: [],
      task_group: "PROFILE" as const,
      order,
      prerequisites: [],
    });
    api.listDocuments.mockResolvedValue([doc] as never);
    api.listStageOptions.mockResolvedValue([
      { id: 70, journey_template_id: 7, title: "Ngày 1", template_title: "Lộ trình onboarding" },
    ]);
    api.listActiveJobs.mockResolvedValue([]);
    api.createAiTaskProposalJob.mockResolvedValue({ id: 500 } as never);
    api.getJob.mockResolvedValue(
      jobOf({
        status: "SUCCEEDED",
        progress_percent: 100,
        result: {
          documents: [
            {
              version_id: 31,
              document_title: "Hướng dẫn ngày 1",
              version_label: "1.0",
              status: "DONE",
              proposals: [proposal("Nhận laptop", 1), proposal("Cài Outlook", 2)],
              skipped_info_sections: [{ section_id: 9, heading: "Giới thiệu công ty" }],
            },
          ],
        },
      }),
    );
    const release: Array<() => void> = [];
    let nextId = 100;
    api.acceptAiTaskProposal.mockImplementation(
      () => new Promise((resolve) => release.push(() => resolve({ id: ++nextId } as never))),
    );

    render(wrap(<AiTasksPage />));
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.document.pick) }));
    fireEvent.click(await screen.findByRole("button", { name: /Hướng dẫn ngày 1/ }));
    fireEvent.click(screen.getByRole("button", { name: t.document.done }));
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.run.submitCount.replace("{count}", "1")) }));
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.propose.acceptPending) }));
    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.propose.addToTasks) }));

    // Mục AI bỏ qua vì chỉ là thông tin vẫn được báo để HR tự kiểm tra.
    expect(await screen.findByText(/AI coi 1 mục là chỉ có thông tin nên không tạo task/)).toBeInTheDocument();
    expect(screen.getByText("Giới thiệu công ty")).toBeInTheDocument();
    expect(await screen.findByText("Đang tạo task 0/2")).toBeInTheDocument();
    await waitFor(() => expect(release).toHaveLength(1));
    await act(async () => release[0]!());
    expect(await screen.findByText("Đang tạo task 1/2")).toBeInTheDocument();
    await waitFor(() => expect(release).toHaveLength(2));
    await act(async () => release[1]!());
    await waitFor(() => expect(screen.queryByTestId("creating-progress")).not.toBeInTheDocument());
    expect(api.acceptAiTaskProposal).toHaveBeenCalledTimes(2);
  });
});
