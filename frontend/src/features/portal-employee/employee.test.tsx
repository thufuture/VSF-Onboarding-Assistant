import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { portalHrApi } from "@/features/portal-hr/api";
import { vigaApi } from "@/features/viga/api";
import type { VigaAnswerResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";
import type {
  EmployeeJourneyResponseDTO,
  EmployeeTaskResponseDTO,
  JourneyNoticeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { EmployeeShell } from "./EmployeeShell";
import { JourneyProvider } from "./JourneyProvider";
import { EmployeeTaskPage } from "./TaskPage";
import { EmployeeTasksPage } from "./TasksPage";
import { EmployeeTicketsPage } from "./TicketsPage";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...rest }: { href: string | { pathname: string }; children: ReactNode; className?: string }) => (
    <a href={`/vi${typeof href === "string" ? href : href.pathname}`} {...rest}>
      {children}
    </a>
  ),
  usePathname: () => "/me/tasks",
  useRouter: () => ({ push, replace: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams() }));
vi.mock("@/features/chat/DocumentModal", () => ({
  DocumentModal: ({ documentTitle, sectionHeading, quote }: { documentTitle: string; sectionHeading: string | null; quote?: string | null }) => (
    <div data-quote={quote ?? ""} role="dialog" aria-label="tài liệu">
      {`Mở: ${documentTitle} / ${sectionHeading}`}
    </div>
  ),
}));
vi.mock("next-intl", async () => {
  const actual = await vi.importActual<typeof import("next-intl")>("next-intl");
  return { ...actual, useLocale: () => "vi" };
});
vi.mock("@/features/auth/session", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/auth/session")>();
  return { ...original, authApi: { login: vi.fn(), me: vi.fn(), refresh: vi.fn(), logout: vi.fn() } };
});
vi.mock("@/features/portal-hr/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/portal-hr/api")>();
  return {
    ...original,
    portalHrApi: {
      getMyJourney: vi.fn(),
      completeTask: vi.fn(),
      listMyJourneyNotices: vi.fn(),
      markJourneyNoticeRead: vi.fn(),
      previewJourneyChange: vi.fn(),
      acceptJourneyChange: vi.fn(),
      dismissJourneyChange: vi.fn(),
      acceptAllJourneyChanges: vi.fn(),
    },
  };
});

vi.mock("@/features/viga/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/viga/api")>();
  return {
    ...original,
    vigaApi: {
      ask: vi.fn(),
      listMyTickets: vi.fn(),
      markTaskOpened: vi.fn(),
      listConversations: vi.fn(),
      getConversation: vi.fn(),
      deleteConversation: vi.fn(),
      renameConversation: vi.fn(),
      createTicket: vi.fn(),
      getTicket: vi.fn(),
    },
  };
});

function answer(overrides: Partial<VigaAnswerResponseDTO>): VigaAnswerResponseDTO {
  return {
    conversation_id: 1,
    message_id: 1,
    new_conversation: true,
    response_type: "INFO",
    message: "",
    message_key: null,
    message_params: {},
    claims: [],
    blocking_tasks: [],
    suggested_actions: [],
    sources: [],
    can_report_to_hr: false,
    assumed_task_title: null,
    route: "SHORTCUT",
    ...overrides,
  };
}

const USER: SessionUserResponseDTO = {
  id: 7,
  email: "user1@vsf-demo.example",
  display_name: "Nguyễn Văn An",
  role: "USER",
  department: "Khối Dữ liệu",
  expires_at: "2026-09-30T10:00:00Z",
};

function task(overrides: Partial<EmployeeTaskResponseDTO> & { id: number; title: string }): EmployeeTaskResponseDTO {
  return {
    task_template_id: overrides.id,
    body_markdown: "## Vì sao phải làm\nĐể có thiết bị làm việc.\n\n## Các bước\n1. Lên tầng 12\n2. Ký nhận máy",
    required: true,
    stage_id: 1,
    stage_title: "Ngày 1",
    stage_sort_order: 1,
    sort_order: overrides.id,
    task_group: "DEVICE",
    status: "READY",
    completed_at: null,
    prerequisites: [],
    ...overrides,
  };
}

const LAPTOP = task({ id: 11, title: "Nhận laptop" });
const SIGNATURE = task({
  id: 12,
  title: "Chữ ký email",
  status: "LOCKED",
  prerequisites: [{ title: "Nhận laptop", done: false }],
});

const JOURNEY: EmployeeJourneyResponseDTO = {
  id: 5,
  journey_template_id: 2,
  journey_title: "Lộ trình nhân viên mới",
  started_at: "2026-09-28T02:00:00Z",
  tasks: [LAPTOP, SIGNATURE],
};

function renderEmployee(ui: ReactNode) {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider initialUser={USER}>
        <JourneyProvider>
          <EmployeeShell>{ui}</EmployeeShell>
        </JourneyProvider>
      </SessionProvider>
    </NextIntlClientProvider>,
  );
}

const m = viMessages.employee;

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  vi.mocked(portalHrApi.getMyJourney).mockResolvedValue(JOURNEY);
  vi.mocked(portalHrApi.completeTask).mockResolvedValue({ ...LAPTOP, status: "DONE" });
  vi.mocked(portalHrApi.listMyJourneyNotices).mockResolvedValue([]);
  vi.mocked(portalHrApi.markJourneyNoticeRead).mockResolvedValue();
  vi.mocked(portalHrApi.previewJourneyChange).mockResolvedValue({
    change_id: 90,
    kind: "MODIFIED",
    keeps_done: false,
    removes_task: false,
    also_update: [],
    locked_until: [],
  });
  vi.mocked(portalHrApi.acceptJourneyChange).mockResolvedValue({ updated_change_ids: [90] });
  vi.mocked(portalHrApi.dismissJourneyChange).mockResolvedValue();
  vi.mocked(vigaApi.listMyTickets).mockResolvedValue([]);
  vi.mocked(vigaApi.markTaskOpened).mockResolvedValue();
});

describe("Khung của nhân viên mới", () => {
  it("hiện đủ mục chức năng; sáng tối và ngôn ngữ nằm trong thẻ tài khoản", async () => {
    renderEmployee(<p>nội dung</p>);

    const nav = screen.getByRole("navigation", { name: m.navLabel });
    for (const label of [m.nav.overview, m.nav.tasks, m.nav.tickets]) {
      expect(within(nav).getByRole("link", { name: label })).toBeInTheDocument();
    }

    expect(screen.queryByText(USER.email)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: m.accountMenu }));

    const menu = screen.getByRole("menu", { name: m.accountMenu });
    expect(within(menu).getByText(USER.email)).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: new RegExp(m.menu.profile) })).toHaveAttribute("href", "/vi/me/profile");
    expect(within(menu).getByRole("menuitem", { name: new RegExp(m.darkMode) })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: /English/ })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: new RegExp(m.menu.logout) })).toBeInTheDocument();
  });

  it("chuông đếm số chưa đọc và mở thẻ thông báo suy ra từ lộ trình thật", async () => {
    renderEmployee(<p>nội dung</p>);

    const bell = await screen.findByRole("button", { name: m.nav.notifications });
    // 1 việc làm được ngay + 1 nhắc việc của ngày + 1 lời chào = 3 thông báo chưa đọc.
    await waitFor(() => expect(within(bell).getByText("3")).toBeInTheDocument());

    fireEvent.click(bell);
    const card = screen.getByRole("menu", { name: m.nav.notifications });
    expect(within(card).getByText(`Bạn làm được ngay: ${LAPTOP.title}`)).toBeInTheDocument();
    expect(within(card).queryByRole("link")).not.toBeInTheDocument(); // không còn trang thông báo riêng
    expect(within(card).getByRole("tab", { name: /Chưa đọc/ })).toBeInTheDocument();

    fireEvent.click(within(card).getByRole("button", { name: new RegExp(m.notifications.markAll) }));
    await waitFor(() => expect(within(bell).queryByText("3")).not.toBeInTheDocument());
  });

  it("mở ngăn Viga, hỏi qua API thật và hiện câu trả lời đã dịch theo khóa", async () => {
    vi.mocked(vigaApi.ask).mockResolvedValue(
      answer({
        response_type: "DAY_PLAN",
        message: "tiếng Việt dự phòng",
        message_key: "dayPlan",
        message_params: { day: "Ngày 1", ready: 1, total: 2 },
      }),
    );
    renderEmployee(<p>nội dung</p>);
    await screen.findByRole("button", { name: m.nav.notifications });

    fireEvent.click(screen.getByRole("button", { name: new RegExp(m.askViga) }));
    const panel = screen.getByRole("complementary", { name: m.viga.title });
    expect(within(panel).getByText(m.viga.subtitle)).toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("button", { name: m.viga.quick.q1 }));

    expect(await screen.findByText("Ngày 1: bạn làm được ngay 1 việc trên tổng 2 việc của ngày.")).toBeInTheDocument();
    expect(screen.getByText(m.viga.type.DAY_PLAN)).toBeInTheDocument();
    // Giao diện chỉ gửi câu hỏi và mã cuộc trò chuyện, không gửi mã việc.
    expect(vigaApi.ask).toHaveBeenCalledWith({ question: m.viga.quick.q1, conversation_id: null });
  });
});

describe("Trang Yêu cầu: tạo ticket", () => {
  it("nút Tạo ticket mở hộp, gửi câu hỏi tự viết cho HR rồi mở ticket vừa tạo", async () => {
    const created = {
      id: 31,
      subject: "Chưa đăng nhập được Outlook",
      status: "OPEN",
      source: "MANUAL",
      created_at: "2026-10-06T05:00:00Z",
      updated_at: "2026-10-06T05:00:00Z",
      requester_name: USER.display_name,
      requester_email: USER.email,
      team_name: "IT",
      assigned_hr_name: null,
      related_task_title: null,
      message_count: 1,
      last_sender_is_staff: false,
      resolution_note: null,
    } as const;
    vi.mocked(vigaApi.createTicket).mockResolvedValue(created);
    vi.mocked(vigaApi.getTicket).mockReturnValue(new Promise(() => undefined));
    renderEmployee(<EmployeeTicketsPage />);

    fireEvent.click(await screen.findByRole("button", { name: viMessages.viga.ticket.create }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(viMessages.employee.viga.report.newTitle)).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText(viMessages.employee.viga.report.question), {
      target: { value: "  Chưa đăng nhập được Outlook  " },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: new RegExp(viMessages.employee.viga.report.send) }));

    await waitFor(() =>
      expect(vigaApi.createTicket).toHaveBeenCalledWith({
        question: "Chưa đăng nhập được Outlook",
        note: null,
        employee_task_id: null,
        conversation_id: null,
        attachment_ids: [],
      }),
    );
    await waitFor(() => expect(vigaApi.getTicket).toHaveBeenCalledWith(31));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Trang Nhiệm vụ", () => {
  it("hiện ngày và việc của ngày, bấm một việc thì mở trang chi tiết", async () => {
    renderEmployee(<EmployeeTasksPage />);

    expect(await screen.findByRole("heading", { level: 2, name: "Ngày 1" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: LAPTOP.title }));
    expect(push).toHaveBeenCalledWith(`/me/tasks/${LAPTOP.id}`);
  });

  it("chuyển sang cách xem danh sách thì mỗi việc là một dòng có trạng thái", async () => {
    renderEmployee(<EmployeeTasksPage />);

    fireEvent.click(await screen.findByRole("button", { name: new RegExp(m.tasks.modeList) }));

    const row = screen.getByRole("button", { name: new RegExp(SIGNATURE.title) });
    expect(within(row).getByText(m.task.state.locked)).toBeInTheDocument();
    expect(within(row).getByText(`Cần xong: ${LAPTOP.title}`)).toBeInTheDocument();
  });

  it("HR chưa thêm lộ trình thì nhân viên chỉ thấy lời báo, không có nút tự tạo", async () => {
    const { PortalError } = await vi.importActual<typeof import("@/features/portal-hr/api")>("@/features/portal-hr/api");
    vi.mocked(portalHrApi.getMyJourney).mockRejectedValue(new PortalError("unavailable", "NO_JOURNEY"));

    renderEmployee(<EmployeeTasksPage />);

    expect(await screen.findByTestId("no-journey")).toHaveTextContent(m.journeyProblem.needsCreateBody);
    expect(screen.queryByRole("button", { name: /Tạo lộ trình/ })).not.toBeInTheDocument();
  });

  it("lộ trình chưa được gán thì báo rõ cần liên hệ HR", async () => {
    const { PortalError } = await vi.importActual<typeof import("@/features/portal-hr/api")>("@/features/portal-hr/api");
    vi.mocked(portalHrApi.getMyJourney).mockRejectedValue(new PortalError("unavailable", "NO_TEAM_ASSIGNED"));

    renderEmployee(<EmployeeTasksPage />);

    expect(await screen.findByText(m.journeyProblem.noJourney)).toBeInTheDocument();
  });
});

describe("Trang chi tiết việc", () => {
  it("việc làm được ngay: hiện các bước và cho tự xác nhận hoàn thành", async () => {
    renderEmployee(<EmployeeTaskPage taskId={LAPTOP.id} />);

    expect(await screen.findByRole("heading", { level: 1, name: LAPTOP.title })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: m.taskPage.steps })).toBeInTheDocument();
    expect(screen.getByText("Lên tầng 12")).toBeInTheDocument();
    expect(screen.getByText(m.taskPage.readyHint)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: new RegExp(m.task.markDone) }));
    await waitFor(() => expect(portalHrApi.completeTask).toHaveBeenCalledWith(LAPTOP.id));
    expect(await screen.findByText(`Đã hoàn thành: ${LAPTOP.title}`)).toBeInTheDocument();
  });

  it("việc có nguồn: hiện thẻ Nguồn tài liệu và mở tài liệu đúng mục, đúng đoạn trích", async () => {
    const withSources = task({
      id: 11,
      title: "Nhận laptop",
      sources: [
        {
          document_title: "Hướng dẫn ngày 1",
          version_label: "1.0",
          version_id: 31,
          document_url: "x",
          section_heading: "8. Nhận laptop",
          quote: "Nhận laptop tại tầng 12",
        },
      ],
    });
    vi.mocked(portalHrApi.getMyJourney).mockResolvedValue({ ...JOURNEY, tasks: [withSources, SIGNATURE] });
    renderEmployee(<EmployeeTaskPage taskId={11} />);

    expect(await screen.findByRole("heading", { name: m.taskPage.sourcesTitle })).toBeInTheDocument();
    expect(screen.getByText("Nhận laptop tại tầng 12")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: viMessages.taskSources.view }));

    const viewer = screen.getByRole("dialog", { name: "tài liệu" });
    expect(viewer).toHaveTextContent("Mở: Hướng dẫn ngày 1 / 8. Nhận laptop");
    expect(viewer).toHaveAttribute("data-quote", "Nhận laptop tại tầng 12");
  });

  it("việc không có nguồn thì không hiện thẻ Nguồn tài liệu", async () => {
    renderEmployee(<EmployeeTaskPage taskId={LAPTOP.id} />);

    await screen.findByRole("heading", { level: 1, name: LAPTOP.title });
    expect(screen.queryByRole("heading", { name: m.taskPage.sourcesTitle })).not.toBeInTheDocument();
  });

  it("việc đang khóa: nêu việc phải xong trước, không cho bấm hoàn thành", async () => {
    renderEmployee(<EmployeeTaskPage taskId={SIGNATURE.id} />);

    expect(await screen.findByRole("heading", { level: 1, name: SIGNATURE.title })).toBeInTheDocument();
    expect(screen.getByText(m.taskPage.lockedTitle)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: new RegExp(m.task.markDone) })).toBeDisabled();

    const prereq = screen.getByRole("heading", { name: m.taskPage.prereqTitle }).closest("section");
    expect(within(prereq as HTMLElement).getByText(LAPTOP.title)).toBeInTheDocument();
  });

  it('nút "Hỏi Viga về việc này" mở ngăn Viga kèm câu trả lời cho đúng việc', async () => {
    renderEmployee(<EmployeeTaskPage taskId={SIGNATURE.id} />);

    vi.mocked(vigaApi.ask).mockResolvedValue(
      answer({
        response_type: "PREREQUISITE_REQUIRED",
        message_key: "locked",
        message_params: { title: SIGNATURE.title, blocker: LAPTOP.title },
        blocking_tasks: [{ task_id: LAPTOP.id, title: LAPTOP.title, state: "ready" }],
        suggested_actions: [{ type: "OPEN_TASK", title: LAPTOP.title, task_id: LAPTOP.id, stage_id: null }],
      }),
    );
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(m.taskPage.askViga) }));

    const panel = screen.getByRole("complementary", { name: m.viga.title });
    expect(await within(panel).findByText(m.viga.type.PREREQUISITE_REQUIRED)).toBeInTheDocument();
    expect(
      within(panel).getByText(`Bạn chưa làm được “${SIGNATURE.title}” vì cần hoàn thành “${LAPTOP.title}” trước.`),
    ).toBeInTheDocument();
    expect(vigaApi.ask).toHaveBeenCalledWith({
      question: viMessages.employee.taskPage.askVigaQuestion.replace("{title}", SIGNATURE.title),
      conversation_id: null,
    });
    fireEvent.click(within(panel).getByRole("button", { name: `Mở: ${LAPTOP.title}` }));
    expect(push).toHaveBeenCalledWith(`/me/tasks/${LAPTOP.id}`);
  });

  it("mở trang việc thì ghi nhận việc vừa mở để Viga hiểu \"việc này\"", async () => {
    renderEmployee(<EmployeeTaskPage taskId={SIGNATURE.id} />);

    await screen.findByRole("heading", { level: 1, name: SIGNATURE.title });

    await waitFor(() => expect(vigaApi.markTaskOpened).toHaveBeenCalledWith(SIGNATURE.id));
  });

  it("việc không có trong lộ trình thì báo rõ", async () => {
    renderEmployee(<EmployeeTaskPage taskId={999} />);

    expect(await screen.findByRole("heading", { level: 1, name: m.taskPage.notFoundTitle })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: m.taskPage.backToTasks })).toHaveAttribute("href", "/vi/me/tasks");
  });
});

const NOTICE: JourneyNoticeResponseDTO = {
  id: 70,
  journey_stage_id: 1,
  stage_title: "Ngày 1",
  version_no: 2,
  created_at: "2026-09-30T03:00:00Z",
  read_at: null,
  changes: [
    {
      id: 90,
      notice_id: 70,
      kind: "MODIFIED",
      status: "PENDING",
      task_title: LAPTOP.title,
      employee_task_id: LAPTOP.id,
      employee_status: "READY",
      stage_title: "Ngày 1",
      before: { body_markdown: "Nhận laptop tại tầng 12" },
      after: { body_markdown: "Nhận laptop tại tầng 5" },
      changed_fields: ["body_markdown"],
      informational: false,
    },
  ],
};

describe("Chỉnh sửa lộ trình do HR áp dụng", () => {
  beforeEach(() => {
    vi.mocked(portalHrApi.listMyJourneyNotices).mockResolvedValue([NOTICE]);
  });

  it("chuông báo ngày có chỉnh sửa và trang Nhiệm vụ nhắc có việc chờ quyết định", async () => {
    renderEmployee(<EmployeeTasksPage />);

    expect(await screen.findByTestId("pending-changes-banner")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: m.nav.notifications }));
    const card = screen.getByRole("menu", { name: m.nav.notifications });
    expect(within(card).getByText("Ngày 1 có chỉnh sửa")).toBeInTheDocument();
  });

  it("trang việc hiện trước/sau và ghi chú; bấm Cập nhật gọi API rồi nạp lại lộ trình", async () => {
    renderEmployee(<EmployeeTaskPage taskId={LAPTOP.id} />);

    const cardEl = await screen.findByTestId("change-card");
    expect(within(cardEl).getByText("Nhận laptop tại tầng 12")).toBeInTheDocument();
    expect(within(cardEl).getByText("Nhận laptop tại tầng 5")).toBeInTheDocument();
    expect(await within(cardEl).findByText(m.changes.noteKeepStatus)).toBeInTheDocument();
    expect(portalHrApi.previewJourneyChange).toHaveBeenCalledWith(90);

    fireEvent.click(within(cardEl).getByRole("button", { name: m.changes.accept }));
    await waitFor(() => expect(portalHrApi.acceptJourneyChange).toHaveBeenCalledWith(90));
    // Sau khi cập nhật: nạp lại lộ trình và thông báo.
    await waitFor(() => expect(vi.mocked(portalHrApi.getMyJourney).mock.calls.length).toBeGreaterThan(1));
  });

  it("Giữ bản cũ chỉ gọi dismiss, không gọi accept", async () => {
    renderEmployee(<EmployeeTaskPage taskId={LAPTOP.id} />);

    const cardEl = await screen.findByTestId("change-card");
    fireEvent.click(within(cardEl).getByRole("button", { name: m.changes.keepOld }));

    await waitFor(() => expect(portalHrApi.dismissJourneyChange).toHaveBeenCalledWith(90));
    expect(portalHrApi.acceptJourneyChange).not.toHaveBeenCalled();
  });
});
