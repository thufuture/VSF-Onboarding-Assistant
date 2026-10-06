import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { portalHrApi } from "@/features/portal-hr/api";
import type {
  RolloutRowResponseDTO,
  TemplateNodeResponseDTO,
  VersionNodeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { RolloutModal } from "./RolloutModal";
import { StageVersionBar } from "./StageVersionBar";
import { TaskManagementPage } from "./TaskManagementPage";

vi.mock("@/features/portal-hr/api", () => {
  class PortalError extends Error {
    readonly code: string;
    readonly apiCode: string | null;
    constructor(code: string, apiCode: string | null = null) {
      super(code);
      this.code = code;
      this.apiCode = apiCode;
    }
  }
  return {
    PortalError,
    portalHrApi: {
      listMyTemplates: vi.fn(),
      createStageVersion: vi.fn(),
      previewApplyVersion: vi.fn(),
      applyStageVersion: vi.fn(),
      deleteStageVersion: vi.fn(),
      getVersionRollout: vi.fn(),
      createTaskInVersion: vi.fn(),
      createTaskManual: vi.fn(),
      listEmployees: vi.fn(),
      createEmployeeJourney: vi.fn(),
    },
  };
});
vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
  usePathname: () => "/admin/tasks",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams() }));

const api = vi.mocked(portalHrApi);
const t = viMessages.portalTasks;

function version(overrides: Partial<VersionNodeResponseDTO> & { id: number; version_no: number }): VersionNodeResponseDTO {
  return {
    status: "DRAFT",
    note: null,
    based_on_version_id: null,
    applied_at: null,
    created_at: "2026-10-01T00:00:00Z",
    tasks: [],
    ...overrides,
  };
}

const APPLIED = version({
  id: 1,
  version_no: 1,
  status: "APPLIED",
  tasks: [
    {
      id: 11,
      journey_stage_id: 5,
      stage_version_id: 1,
      title: "Nhận laptop",
      body_markdown: "nội dung",
      required: true,
      sort_order: 1,
      team_id: null,
      depends_on: [],
      task_group: "DEVICE",
    },
  ],
});
const DRAFT = version({ id: 2, version_no: 2, status: "DRAFT", based_on_version_id: 1 });

function tree(versions: VersionNodeResponseDTO[], defaultId: number): TemplateNodeResponseDTO[] {
  return [
    {
      id: 3,
      code: "tpl",
      title: "Lộ trình",
      status: "DRAFT",
      team_id: null,
      stages: [
        {
          id: 5,
          title: "Ngày 1",
          sort_order: 1,
          tasks: versions.find((v) => v.id === defaultId)?.tasks ?? [],
          versions,
          default_version_id: defaultId,
        },
      ],
    },
  ];
}

function withIntl(ui: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      {ui}
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Thanh phiên bản của một ngày", () => {
  const handlers = {
    onSelect: vi.fn(),
    onCreateDraft: vi.fn(),
    onApply: vi.fn(),
    onDelete: vi.fn(),
    onRollout: vi.fn(),
  };

  it("bản đang áp dụng: chỉ xem, có nút tạo nháp và theo dõi triển khai, không có Áp dụng hay Xóa nháp", () => {
    withIntl(<StageVersionBar busy={false} selectedId={1} versions={[APPLIED, DRAFT]} {...handlers} />);

    expect(screen.getByRole("button", { name: new RegExp(t.versions.createDraft) })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: new RegExp(t.versions.rollout) })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(`^${t.versions.apply}$`) })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(t.versions.deleteDraft) })).not.toBeInTheDocument();
    expect(screen.getByTitle(t.versions.hint.APPLIED)).toBeInTheDocument();
  });

  it("bản nháp: có Áp dụng và Xóa nháp, bấm Áp dụng trả đúng phiên bản", () => {
    withIntl(<StageVersionBar busy={false} selectedId={2} versions={[APPLIED, DRAFT]} {...handlers} />);

    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.versions.apply) }));
    expect(handlers.onApply).toHaveBeenCalledWith(DRAFT);
    expect(screen.getByRole("button", { name: new RegExp(t.versions.deleteDraft) })).toBeInTheDocument();
  });

  it("chọn bản khác qua danh sách phiên bản", () => {
    withIntl(<StageVersionBar busy={false} selectedId={1} versions={[APPLIED, DRAFT]} {...handlers} />);

    fireEvent.click(screen.getByRole("button", { name: t.versions.label }));
    fireEvent.click(screen.getByRole("option", { name: /Bản 2/ }));
    expect(handlers.onSelect).toHaveBeenCalledWith(2);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument(); // chọn xong thì đóng danh sách
  });
});

describe("Bảng theo dõi triển khai", () => {
  it("tóm tắt và liệt kê từng nhân viên theo tình trạng", async () => {
    const rows: RolloutRowResponseDTO[] = [
      { notice_id: 1, user_id: 7, display_name: "Nguyễn Văn An", email: "an@x", state: "UPDATED", pending: 0, accepted: 2, dismissed: 0, total: 2, read_at: null },
      { notice_id: 2, user_id: 8, display_name: "Lê Thị Bình", email: "binh@x", state: "UNSEEN", pending: 2, accepted: 0, dismissed: 0, total: 2, read_at: null },
    ];
    api.getVersionRollout.mockResolvedValue(rows);

    withIntl(<RolloutModal onClose={vi.fn()} versionId={1} versionNo={1} />);

    expect(await screen.findByText("Nguyễn Văn An")).toBeInTheDocument();
    expect(screen.getByTestId("rollout-summary")).toHaveTextContent("2 nhân viên: 1 chưa xem, 0 đã xem, 1 đã cập nhật, 0 giữ bản cũ.");
    expect(screen.getByText(viMessages.portalTasks.rollout.state.UNSEEN)).toBeInTheDocument();
  });
});

describe("Quản lý task theo phiên bản", () => {
  it("bản đang áp dụng chỉ xem: nút thêm task bị khóa; tạo bản nháp xong chuyển sang bản nháp", async () => {
    api.listMyTemplates.mockResolvedValue(tree([APPLIED], 1));
    api.createStageVersion.mockResolvedValue({
      id: 2,
      journey_stage_id: 5,
      version_no: 2,
      status: "DRAFT",
      note: null,
      based_on_version_id: 1,
      applied_at: null,
      created_at: "2026-10-02T00:00:00Z",
      task_count: 1,
    });

    withIntl(<TaskManagementPage />);

    const addButtons = await screen.findAllByRole("button", { name: new RegExp(t.addTask) });
    for (const button of addButtons) expect(button).toBeDisabled();

    // Sau khi tạo nháp, máy chủ trả cây có thêm bản 2: giao diện chọn luôn bản vừa tạo.
    api.listMyTemplates.mockResolvedValue(tree([APPLIED, { ...DRAFT, tasks: APPLIED.tasks.map((x) => ({ ...x, id: 21, stage_version_id: 2 })) }], 1));
    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.versions.createDraft) }));
    // Phải qua hộp xác nhận: chưa xác nhận thì chưa tạo gì.
    const dialog = await screen.findByRole("dialog");
    expect(api.createStageVersion).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: t.versions.createDraftConfirm }));

    await waitFor(() => expect(api.createStageVersion).toHaveBeenCalledWith(5, { from_version_id: 1 }));
    await waitFor(() => {
      for (const button of screen.getAllByRole("button", { name: new RegExp(t.addTask) })) expect(button).not.toBeDisabled();
    });
  });

  it("Áp dụng: xem trước số việc đổi và nhân viên, xác nhận mới gọi áp dụng", async () => {
    api.listMyTemplates.mockResolvedValue(tree([APPLIED, DRAFT], 1));
    api.previewApplyVersion.mockResolvedValue({ modified: 2, added: 1, removed: 0, employee_count: 4, has_applied_before: true });
    api.applyStageVersion.mockResolvedValue({
      version: { id: 2, journey_stage_id: 5, version_no: 2, status: "APPLIED", note: null, based_on_version_id: 1, applied_at: "x", created_at: "x", task_count: 1 },
      notified_count: 4,
    });

    withIntl(<TaskManagementPage />);

    fireEvent.click(await screen.findByRole("button", { name: t.versions.label }));
    fireEvent.click(screen.getByRole("option", { name: /Bản 2/ }));
    fireEvent.click(screen.getByRole("button", { name: new RegExp(`^${t.versions.apply}$`) }));

    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/Việc sửa: 2, việc thêm: 1, việc bỏ: 0/)).toBeInTheDocument();
    expect(within(dialog).getByText(/4 nhân viên đã tạo KHÔNG tự đổi/)).toBeInTheDocument();
    expect(api.applyStageVersion).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByRole("button", { name: t.apply.confirm }));
    await waitFor(() => expect(api.applyStageVersion).toHaveBeenCalledWith(2));
  });
});

describe("Thêm lộ trình cho nhân viên", () => {
  it("bấm Thêm lộ trình mở hộp xác nhận, xác nhận mới gọi API", async () => {
    const { EmployeesPage } = await import("./EmployeesPage");
    const person = {
      id: 9,
      display_name: "Trần Anh Thư",
      email: "thu@x",
      department: null,
      journey_started: false,
      tasks_done: 0,
      tasks_total: 0,
      current_task_title: null,
      current_stage_title: null,
      current_status: null,
    };
    vi.mocked(portalHrApi.listEmployees).mockResolvedValue([person]);
    vi.mocked(portalHrApi.createEmployeeJourney).mockResolvedValue({ journey_id: 1, created: true });

    withIntl(<EmployeesPage />);

    fireEvent.click(await screen.findByRole("button", { name: viMessages.portalEmployees.addJourney }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/Thêm lộ trình cho Trần Anh Thư/)).toBeInTheDocument();
    expect(portalHrApi.createEmployeeJourney).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByRole("button", { name: viMessages.portalEmployees.addJourneyConfirm }));
    await waitFor(() => expect(portalHrApi.createEmployeeJourney).toHaveBeenCalledWith(9));
  });
});
