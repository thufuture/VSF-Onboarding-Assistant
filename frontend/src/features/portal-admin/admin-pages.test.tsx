import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { portalAdminApi } from "@/features/portal-admin/api";
import type {
  AdminMembershipResponseDTO,
  AdminTeamResponseDTO,
  AdminUserResponseDTO,
} from "@/features/portal-admin/dto/responseDTO/admin.response";

import { AdminMembersPage } from "./AdminMembersPage";
import { AdminTeamsPage } from "./AdminTeamsPage";
import { AdminUsersPage } from "./AdminUsersPage";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...rest }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href}`} {...rest}>
      {children}
    </a>
  ),
  usePathname: () => "/admin",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/features/portal-admin/api", () => ({
  portalAdminApi: {
    getDashboard: vi.fn(),
    listUsers: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    resetPassword: vi.fn(),
    setUserStatus: vi.fn(),
    listTeams: vi.fn(),
    createTeam: vi.fn(),
    updateTeam: vi.fn(),
    setTeamStatus: vi.fn(),
    copyTemplate: vi.fn(),
    listMemberships: vi.fn(),
    addMembership: vi.fn(),
    removeMembership: vi.fn(),
    getTemplateOverview: vi.fn(),
    listAuditLogs: vi.fn(),
  },
}));

const ADMIN: SessionUserResponseDTO = {
  id: 1,
  email: "admin@vsf-demo.example",
  display_name: "Quản trị viên",
  role: "ADMIN",
  department: null,
  expires_at: "2026-09-21T10:00:00Z",
};

function user(id: number, name: string, role: AdminUserResponseDTO["role"], teams: string[] = []): AdminUserResponseDTO {
  return {
    id,
    display_name: name,
    email: `u${id}@vsf-demo.example`,
    role,
    status: "ACTIVE",
    last_login_at: null,
    team_names: teams,
  };
}

function team(id: number, name: string, overrides: Partial<AdminTeamResponseDTO> = {}): AdminTeamResponseDTO {
  return {
    id,
    code: name.toUpperCase().replace(/\s/g, "_"),
    name,
    is_active: true,
    created_at: "2026-09-01T00:00:00Z",
    hr_names: [],
    hr_user_ids: [],
    employee_count: 0,
    hr_count: 0,
    journey_title: null,
    journey_version: null,
    journey_status: null,
    ...overrides,
  };
}

function renderPage(ui: ReactNode) {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider initialUser={ADMIN}>{ui}</SessionProvider>
    </NextIntlClientProvider>,
  );
}

const t = viMessages.portalAdmin;
const api = vi.mocked(portalAdminApi);

beforeEach(() => {
  vi.resetAllMocks();
  api.listTeams.mockResolvedValue([team(4, "Phòng Vinmec"), team(5, "Phòng Du lịch", { journey_title: "Onboarding", journey_version: 1, journey_status: "DRAFT" })]);
});

describe("AdminUsersPage", () => {
  const users = [user(1, "Quản trị viên", "ADMIN"), user(2, "Hoa HR", "HR", ["Phòng Vinmec"]), user(3, "Nam Nhân viên", "USER")];

  it("liệt kê người dùng và lọc theo vai trò", async () => {
    api.listUsers.mockResolvedValue(users);
    renderPage(<AdminUsersPage />);

    expect(await screen.findByText("Hoa HR")).toBeInTheDocument();
    expect(screen.getByText("Nam Nhân viên")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: t.roles.HR }));
    expect(screen.getByText("Hoa HR")).toBeInTheDocument();
    expect(screen.queryByText("Nam Nhân viên")).not.toBeInTheDocument();
  });

  it("khóa tài khoản phải qua modal xác nhận và không cho tự khóa mình", async () => {
    api.listUsers.mockResolvedValue(users);
    api.setUserStatus.mockResolvedValue({ ...users[2], status: "INACTIVE" });
    renderPage(<AdminUsersPage />);
    await screen.findByText("Nam Nhân viên");

    const lockButtons = screen.getAllByTitle(t.users.lock);
    // dòng đầu (chính mình) bị vô hiệu
    expect(lockButtons[0]).toBeDisabled();

    fireEvent.click(lockButtons[2]);
    expect(api.setUserStatus).not.toHaveBeenCalled();
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: t.users.lock }));

    await waitFor(() => expect(api.setUserStatus).toHaveBeenCalledWith(3, "INACTIVE"));
  });

  it("tạo người dùng và hiện mật khẩu tạm đúng một lần", async () => {
    api.listUsers.mockResolvedValue(users);
    api.createUser.mockResolvedValue({ user: user(9, "Mới Vào", "USER"), temporary_password: "Tmp-Pass-123" });
    renderPage(<AdminUsersPage />);
    await screen.findByText("Hoa HR");

    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.users.add) }));
    fireEvent.change(screen.getByLabelText(t.users.form.name), { target: { value: "Mới Vào" } });
    fireEvent.change(screen.getByLabelText(t.users.form.email), { target: { value: "moi@vsf-demo.example" } });
    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.common.save) }));

    await waitFor(() =>
      expect(api.createUser).toHaveBeenCalledWith({
        display_name: "Mới Vào",
        email: "moi@vsf-demo.example",
        role: "USER",
        team_id: null,
      }),
    );
    expect(await screen.findByText("Tmp-Pass-123")).toBeInTheDocument();
  });
});

describe("AdminTeamsPage", () => {
  beforeEach(() => {
    api.listMemberships.mockResolvedValue([]);
    api.listUsers.mockResolvedValue([user(2, "Hoa HR", "HR")]);
  });

  it("lưu trữ phòng ban phải xác nhận trước khi gọi API", async () => {
    api.setTeamStatus.mockResolvedValue(team(4, "Phòng Vinmec", { is_active: false }));
    renderPage(<AdminTeamsPage />);
    await screen.findByText("Phòng Vinmec");

    fireEvent.click(screen.getAllByTitle(t.teams.archive)[0]);
    expect(api.setTeamStatus).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t.teams.archive }));

    await waitFor(() => expect(api.setTeamStatus).toHaveBeenCalledWith(4, false));
  });

  it("chi tiết phòng ban chỉ có nút sao lộ trình khi chưa có lộ trình", async () => {
    renderPage(<AdminTeamsPage />);
    await screen.findByText("Phòng Vinmec");

    fireEvent.click(screen.getAllByTitle(t.teams.detail)[0]);
    expect(within(screen.getByRole("dialog")).getByRole("button", { name: new RegExp(t.teams.copyConfirm) })).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("dialog")).getAllByRole("button", { name: t.common.close })[0]);
    fireEvent.click(screen.getAllByTitle(t.teams.detail)[1]);
    expect(within(screen.getByRole("dialog")).queryByRole("button", { name: new RegExp(t.teams.copyConfirm) })).toBeNull();
  });
});

describe("AdminMembersPage", () => {
  const member: AdminMembershipResponseDTO = {
    team_id: 4,
    team_name: "Phòng Vinmec",
    user_id: 3,
    user_name: "Nam Nhân viên",
    user_email: "u3@vsf-demo.example",
    user_role: "USER",
    team_role: "EMPLOYEE",
    access: "ACTIVE",
    joined_at: "2026-09-02T00:00:00Z",
  };

  it("gỡ thành viên phải xác nhận rồi mới gọi API", async () => {
    api.listMemberships.mockResolvedValue([member]);
    api.listUsers.mockResolvedValue([]);
    api.removeMembership.mockResolvedValue(undefined);
    renderPage(<AdminMembersPage />);
    await screen.findByText("Nam Nhân viên");

    fireEvent.click(screen.getByTitle(t.members.remove));
    expect(api.removeMembership).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t.members.remove }));

    await waitFor(() => expect(api.removeMembership).toHaveBeenCalledWith(4, 3));
  });

  it("hiển thị truy cập bị đóng khi phòng ban đã lưu trữ", async () => {
    api.listMemberships.mockResolvedValue([{ ...member, access: "BLOCKED_TEAM" }]);
    api.listUsers.mockResolvedValue([]);
    renderPage(<AdminMembersPage />);

    const cell = await screen.findByText(t.members.access.BLOCKED_TEAM, { selector: "span" });
    expect(cell).toBeInTheDocument();
  });
});
