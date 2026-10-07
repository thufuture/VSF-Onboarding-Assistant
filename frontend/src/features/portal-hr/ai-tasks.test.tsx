import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import { portalHrApi } from "@/features/portal-hr/api";

import { AiTasksPage } from "./AiTasksPage";

vi.mock("@/features/portal-hr/api", () => {
  class PortalError extends Error {
    readonly code: string;
    readonly apiCode: string | null;
    constructor(code: string, apiCode: string | null = null) {
      super(apiCode ?? code);
      this.code = code;
      this.apiCode = apiCode;
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
      proposeAiTasksFromSections: vi.fn(),
      getDocumentSectionOrder: vi.fn(),
    },
  };
});
vi.mock("@/features/chat/DocumentModal", () => ({
  DocumentModal: ({
    documentTitle,
    sectionHeading,
    actions,
  }: {
    documentTitle: string;
    sectionHeading: string | null;
    actions?: React.ReactNode;
  }) => (
    <div role="dialog">
      <b>{documentTitle}</b>
      <span>mở tại mục: {sectionHeading}</span>
      {actions}
    </div>
  ),
}));
vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
  usePathname: () => "/admin/ai-tasks",
  useRouter: () => ({ replace: vi.fn() }),
}));

const api = vi.mocked(portalHrApi);
const t = viMessages.portalHr;

function renderPage() {
  render(
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
        <AiTasksPage />
      </SessionProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  api.listDocuments.mockResolvedValue([]);
  api.listActiveJobs.mockResolvedValue([]);
});

describe("Tạo ngày cho Tạo task bằng AI", () => {
  it("chưa có ngày nào: nút tạo ngày đầu tiên mở hộp thoại, không bắt nhập mã lộ trình, mã do hệ thống sinh", async () => {
    api.listStageOptions.mockResolvedValue([]);
    api.createJourneyTemplate.mockResolvedValue({ id: 7, title: "Lộ trình onboarding" } as never);
    api.createJourneyStage.mockResolvedValue({ id: 70, title: "Ngày 1" } as never);
    renderPage();

    expect(await screen.findByText(t.stage.empty)).toBeInTheDocument();
    expect(screen.queryByLabelText(t.template.code)).not.toBeInTheDocument(); // không còn biểu mẫu trải trong thẻ
    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.stage.createFirst) }));

    const dialog = within(await screen.findByRole("dialog"));
    expect(dialog.queryByLabelText(t.template.code)).not.toBeInTheDocument();
    expect(dialog.getByLabelText(t.stage.title)).toHaveValue("Ngày 1");
    expect(dialog.getByLabelText(t.template.title)).toBeInTheDocument();
    fireEvent.click(dialog.getByRole("button", { name: new RegExp(t.stage.create) }));

    await waitFor(() => expect(api.createJourneyTemplate).toHaveBeenCalled());
    expect(api.createJourneyTemplate.mock.calls[0]![0].code).toMatch(/^tpl-[a-z0-9]+$/);
    await waitFor(() => expect(api.createJourneyStage).toHaveBeenCalledWith(7, { title: "Ngày 1", sort_order: 1 }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("Ngày 1")).toBeInTheDocument();
  });

  it("đã có lộ trình nháp: ngày mới được thêm vào đúng lộ trình đó, không tạo lộ trình mới và không hỏi tên lộ trình", async () => {
    api.listStageOptions.mockResolvedValue([
      { id: 70, journey_template_id: 7, title: "Ngày 1", template_title: "Lộ trình onboarding" },
    ]);
    api.createJourneyStage.mockResolvedValue({ id: 71, title: "Ngày 2" } as never);
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.stage.addNew) }));
    const dialog = within(await screen.findByRole("dialog"));
    expect(dialog.getByLabelText(t.stage.title)).toHaveValue("Ngày 2"); // gợi ý số ngày kế tiếp
    expect(dialog.queryByLabelText(t.template.title)).not.toBeInTheDocument();
    fireEvent.click(dialog.getByRole("button", { name: new RegExp(t.stage.create) }));

    await waitFor(() => expect(api.createJourneyStage).toHaveBeenCalledWith(7, { title: "Ngày 2", sort_order: 2 }));
    expect(api.createJourneyTemplate).not.toHaveBeenCalled();
  });
});

function proposalOf(title: string, order: number, prerequisites: string[] = []) {
  return {
    title,
    summary: `Vì sao ${title}`,
    instructions_markdown: "Bước 1",
    done_criteria: ["Xong"],
    estimated_minutes: 10,
    source_chunks: [{ document_section_id: order, quote: `Trích ${title}`, heading: `Mục ${order}` }],
    confidence: "HIGH" as const,
    warnings: [],
    task_group: "PROFILE" as const,
    order,
    prerequisites,
  };
}

describe("Tạo task bằng AI: thứ tự và tiên quyết", () => {
  it("tạo task theo thứ tự đề xuất và đổi tiên quyết theo tên thành mã task đã tạo; hiện mục chưa có task", async () => {
    api.listDocuments.mockResolvedValue([
      {
        id: 1,
        title: "Hướng dẫn ngày 1",
        category_name: "Onboarding",
        status: "ACTIVE",
        updated_at: "2026-10-01T00:00:00Z",
        latest_version_id: 31,
        section_count: 17,
        source_key: "day1",
        category_slug: "onboarding",
        owner_name: "HR",
        task_titles: [],
        current_version_label: "1.0",
        version_count: 1,
        draft_count: 0,
        processing_count: 0,
        processing_version_ids: [],
      },
    ]);
    api.listStageOptions.mockResolvedValue([
      { id: 70, journey_template_id: 7, title: "Ngày 1", template_title: "Lộ trình onboarding" },
    ]);
    api.createAiTaskProposalJob.mockResolvedValue({ id: 500 } as never);
    api.getJob.mockResolvedValue({
      id: 500,
      kind: "AI_TASK_PROPOSAL",
      status: "SUCCEEDED",
      progress_percent: 100,
      stage: null,
      error: null,
      document_version_id: null,
      created_at: "2026-10-02T00:00:00Z",
      finished_at: "2026-10-02T00:01:00Z",
      result: {
        documents: [
          {
            version_id: 31,
            document_title: "Hướng dẫn ngày 1",
            version_label: "1.0",
            status: "DONE",
            proposals: [
              proposalOf("Nhận laptop", 1),
              proposalOf("Cài Outlook", 2, ["Nhận laptop"]),
              proposalOf("Gửi ticket", 3, ["Cài Outlook", "Việc không tồn tại"]),
            ],
            uncovered_sections: [{ section_id: 9, heading: "Nghe nội quy" }],
          },
        ],
      },
    } as never);
    let nextId = 100;
    api.acceptAiTaskProposal.mockImplementation(async () => ({ id: ++nextId }) as never);
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.document.pick) }));
    fireEvent.click(await screen.findByRole("button", { name: /Hướng dẫn ngày 1/ }));
    fireEvent.click(screen.getByRole("button", { name: t.document.done }));
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.run.submitCount.replace("{count}", "1")) }));

    expect(await screen.findByText(/1 mục chưa có task/)).toBeInTheDocument();
    expect(screen.getByText("Nghe nội quy")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.propose.acceptPending) }));
    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.propose.addToTasks) }));

    await waitFor(() => expect(api.acceptAiTaskProposal).toHaveBeenCalledTimes(3));
    const calls = api.acceptAiTaskProposal.mock.calls.map(([stageId, body]) => ({ stageId, title: body.title, dependsOn: body.depends_on }));
    expect(calls).toEqual([
      { stageId: 70, title: "Nhận laptop", dependsOn: [] },
      { stageId: 70, title: "Cài Outlook", dependsOn: [101] },
      { stageId: 70, title: "Gửi ticket", dependsOn: [102] }, // tên không có thật bị bỏ, không gửi mã lạ
    ]);
  });
  it("mục AI bỏ qua: Xem mở tài liệu đúng mục, Tạo task chèn vào đúng vị trí theo thứ tự tài liệu và báo task thứ mấy", async () => {
    api.listDocuments.mockResolvedValue([
      {
        id: 1,
        title: "Hướng dẫn ngày 1",
        category_name: "Onboarding",
        status: "ACTIVE",
        updated_at: "2026-10-01T00:00:00Z",
        latest_version_id: 31,
        section_count: 17,
        source_key: "day1",
        category_slug: "onboarding",
        owner_name: "HR",
        task_titles: [],
        current_version_label: "1.0",
        version_count: 1,
        draft_count: 0,
        processing_count: 0,
        processing_version_ids: [],
      },
    ]);
    api.listStageOptions.mockResolvedValue([
      { id: 70, journey_template_id: 7, title: "Ngày 1", template_title: "Lộ trình onboarding" },
    ]);
    api.createAiTaskProposalJob.mockResolvedValue({ id: 500 } as never);
    api.getJob.mockResolvedValue({
      id: 500,
      kind: "AI_TASK_PROPOSAL",
      status: "SUCCEEDED",
      progress_percent: 100,
      stage: null,
      error: null,
      document_version_id: null,
      created_at: "2026-10-02T00:00:00Z",
      finished_at: "2026-10-02T00:01:00Z",
      result: {
        documents: [
          {
            version_id: 31,
            document_title: "Hướng dẫn ngày 1",
            version_label: "1.0",
            status: "DONE",
            // Task A trích mục 1, task B trích mục 20; mục bị bỏ qua là mục 9 nằm GIỮA hai mục đó trong tài liệu.
            proposals: [proposalOf("Task A", 1), proposalOf("Task B", 20)],
            skipped_info_sections: [
              { section_id: 9, heading: "ẢNH ĐẠI DIỆN CHỮ KÝ SLIDE" },
              { section_id: 30, heading: "Mục cuối bị bỏ" },
            ],
          },
        ],
      },
    } as never);
    api.getDocumentSectionOrder.mockResolvedValue([1, 9, 20, 30]);
    api.proposeAiTasksFromSections.mockResolvedValue([proposalOf("Cập nhật ảnh đại diện và chữ ký", 9)]);
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.document.pick) }));
    fireEvent.click(await screen.findByRole("button", { name: /Hướng dẫn ngày 1/ }));
    fireEvent.click(screen.getByRole("button", { name: t.document.done }));
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t.run.submitCount.replace("{count}", "1")) }));

    expect(await screen.findByText(/AI coi 2 mục là chỉ có thông tin/)).toBeInTheDocument();
    // Xem: mở đúng tài liệu, tại đúng mục đó (cùng hộp thoại xem nguồn của task).
    fireEvent.click(screen.getAllByRole("button", { name: t.result.section.view })[0]!);
    const dialog = within(await screen.findByRole("dialog"));
    expect(dialog.getByText("mở tại mục: ẢNH ĐẠI DIỆN CHỮ KÝ SLIDE")).toBeInTheDocument();
    fireEvent.click(dialog.getByRole("button", { name: new RegExp(t.result.section.createFromThis) }));

    await waitFor(() =>
      expect(api.proposeAiTasksFromSections).toHaveBeenCalledWith({ document_version_id: 31, section_ids: [9] }),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    // Chèn giữa Task A và Task B (vị trí 2), không dồn xuống cuối; báo rõ vị trí.
    expect(await screen.findByText(/vị trí Task 2: Cập nhật ảnh đại diện và chữ ký/)).toBeInTheDocument();
    expect(screen.queryByText("ẢNH ĐẠI DIỆN CHỮ KÝ SLIDE")).not.toBeInTheDocument();

    // Loại bỏ: mục còn lại biến khỏi cảnh báo mà không gọi AI.
    fireEvent.click(screen.getByRole("button", { name: t.result.section.dismiss }));
    expect(screen.queryByText("Mục cuối bị bỏ")).not.toBeInTheDocument();
    expect(api.proposeAiTasksFromSections).toHaveBeenCalledTimes(1);
  });
});
