import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { portalHrApi } from "@/features/portal-hr/api";
import type { EmployeeJourneyResponseDTO, EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { EmployeeShell } from "./EmployeeShell";
import { JourneyProvider } from "./JourneyProvider";
import { EmployeeTaskPage } from "./TaskPage";
import { EmployeeTasksPage } from "./TasksPage";

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
  return { ...original, portalHrApi: { getMyJourney: vi.fn(), completeTask: vi.fn() } };
});

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
});

describe("Khung của nhân viên mới", () => {
  it("hiện đủ mục chức năng; sáng tối và ngôn ngữ nằm trong thẻ tài khoản", async () => {
    renderEmployee(<p>nội dung</p>);

    const nav = screen.getByRole("navigation", { name: m.navLabel });
    for (const label of [m.nav.overview, m.nav.tasks, m.nav.progress, m.nav.documents]) {
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
    expect(within(card).getByRole("link", { name: new RegExp(m.notifications.seeAll) })).toHaveAttribute("href", "/vi/me/notifications");

    fireEvent.click(within(card).getByRole("button", { name: new RegExp(m.notifications.markAll) }));
    await waitFor(() => expect(within(bell).queryByText("3")).not.toBeInTheDocument());
  });

  it("mở ngăn Viga và trả lời dựa trên lộ trình, không gọi API", async () => {
    renderEmployee(<p>nội dung</p>);
    await screen.findByRole("button", { name: m.nav.notifications });

    fireEvent.click(screen.getByRole("button", { name: new RegExp(m.askViga) }));
    const panel = screen.getByRole("complementary", { name: m.viga.title });
    expect(within(panel).getByText(m.viga.subtitle)).toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("button", { name: m.viga.quick.q1 }));

    expect(await screen.findByText("Ngày 1: bạn làm được ngay 1 việc trên tổng 2 việc của ngày.")).toBeInTheDocument();
    expect(screen.getByText(m.viga.type.DAY_PLAN)).toBeInTheDocument();
    expect(portalHrApi.getMyJourney).toHaveBeenCalledTimes(1); // chỉ nạp lộ trình, không gọi API hỏi đáp
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

  it("lộ trình chưa được gán thì báo rõ cần liên hệ HR", async () => {
    const { PortalError } = await vi.importActual<typeof import("@/features/portal-hr/api")>("@/features/portal-hr/api");
    vi.mocked(portalHrApi.getMyJourney).mockRejectedValue(new PortalError("unavailable", "NO_TEAM_ASSIGNED"));

    renderEmployee(<EmployeeTasksPage />);

    expect(await screen.findByText(m.tasks.problem.noJourney)).toBeInTheDocument();
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

    fireEvent.click(await screen.findByRole("button", { name: new RegExp(m.taskPage.askViga) }));

    const panel = screen.getByRole("complementary", { name: m.viga.title });
    expect(within(panel).getByText(m.viga.type.PREREQUISITE_REQUIRED)).toBeInTheDocument();
    expect(
      within(panel).getByText(`Bạn chưa làm được “${SIGNATURE.title}” vì cần hoàn thành “${LAPTOP.title}” trước.`),
    ).toBeInTheDocument();
  });

  it("việc không có trong lộ trình thì báo rõ", async () => {
    renderEmployee(<EmployeeTaskPage taskId={999} />);

    expect(await screen.findByRole("heading", { level: 1, name: m.taskPage.notFoundTitle })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: m.taskPage.backToTasks })).toHaveAttribute("href", "/vi/me/tasks");
  });
});
