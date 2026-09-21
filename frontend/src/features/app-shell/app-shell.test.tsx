import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { authApi } from "@/features/auth/session";
import { ChatShell, MOCK_DELAY_MS } from "@/features/chat/ChatShell";

import { AdminPlaceholder } from "./AdminPlaceholder";
import { AppShell } from "./AppShell";

const replace = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...rest }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href}`} {...rest}>
      {children}
    </a>
  ),
  usePathname: () => "/chat",
  useRouter: () => ({ replace }),
}));
vi.mock("next-intl", async () => {
  const actual = await vi.importActual<typeof import("next-intl")>("next-intl");
  return { ...actual, useLocale: () => "vi" };
});
vi.mock("@/features/auth/session", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/auth/session")>();
  return { ...original, authApi: { login: vi.fn(), me: vi.fn(), refresh: vi.fn(), logout: vi.fn() } };
});

const USER: SessionUserResponseDTO = {
  id: 7,
  email: "user1@vsf-demo.example",
  display_name: "Nguyễn Văn A",
  role: "USER",
  department: null,
  expires_at: "2026-09-21T10:00:00Z",
};
const HR: SessionUserResponseDTO = { ...USER, role: "HR", display_name: "HR Demo 1" };

function renderWithSession(ui: ReactNode, user: SessionUserResponseDTO = USER) {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider initialUser={user}>{ui}</SessionProvider>
    </NextIntlClientProvider>,
  );
}

const app = viMessages.app;
const chat = viMessages.chat;

beforeEach(() => {
  replace.mockReset();
  vi.mocked(authApi.logout).mockReset();
  vi.mocked(authApi.refresh).mockReset();
  window.localStorage.clear();
});
afterEach(() => vi.useRealTimers());

describe("AppShell", () => {
  it("thanh bên hiện tên, chữ viết tắt và vai trò của người dùng", () => {
    renderWithSession(<AppShell>nội dung</AppShell>);

    const account = within(screen.getByRole("button", { name: app.signOut }).parentElement as HTMLElement);
    expect(account.getByText(USER.display_name)).toBeInTheDocument();
    expect(account.getByText(app.roles.USER)).toBeInTheDocument();
    expect(account.getByText("NA")).toBeInTheDocument();
    expect(screen.getByText("nội dung")).toBeInTheDocument();
  });

  it("dưới tên hiện phòng ban; chưa có phòng ban thì hiện vai trò", () => {
    const { unmount } = renderWithSession(<AppShell>x</AppShell>, { ...USER, department: "IT Helpdesk" });
    const account = () => within(screen.getByRole("button", { name: app.signOut }).parentElement as HTMLElement);
    expect(account().getByText("IT Helpdesk")).toBeInTheDocument();
    expect(account().queryByText(app.roles.USER)).toBeNull();
    unmount();

    renderWithSession(<AppShell>x</AppShell>);
    expect(account().getByText(app.roles.USER)).toBeInTheDocument();
  });

  it("thanh trên có tiêu đề trang và nhãn phạm vi, cùng chọn ngôn ngữ và sáng/tối", () => {
    renderWithSession(<AppShell>x</AppShell>);

    const bar = within(screen.getByRole("banner"));
    expect(bar.getByText(chat.title)).toBeInTheDocument();
    expect(bar.getByText(chat.scope)).toBeInTheDocument();
    expect(bar.getByLabelText(new RegExp(`^${viMessages.common.language}: `))).toBeInTheDocument();
    expect(bar.getByRole("button", { name: app.darkMode })).toBeInTheDocument();
  });

  it("nhân sự mới: trợ lý hỏi đáp là trang hiện tại, các mục chưa có trang mờ kèm nhãn Sắp có", () => {
    renderWithSession(<AppShell>x</AppShell>);

    const nav = within(screen.getByRole("navigation", { name: app.navigation }));
    expect(nav.getByRole("link", { name: app.nav.chat })).toHaveAttribute("aria-current", "page");
    expect(nav.queryByRole("link", { name: app.nav.admin })).toBeNull();
    for (const key of ["documents", "contacts", "tickets"] as const) {
      expect(nav.getByText(app.nav[key]).closest("[aria-disabled='true']")).not.toBeNull();
    }
    expect(nav.getAllByText(app.nav.soon)).toHaveLength(3);
  });

  it("HR thấy khu quản trị và đường tới trang chat, không có mục Sắp có", () => {
    renderWithSession(<AppShell>x</AppShell>, HR);

    const nav = within(screen.getByRole("navigation", { name: app.navigation }));
    expect(nav.getByRole("link", { name: app.nav.admin })).toHaveAttribute("href", "/vi/admin");
    expect(nav.getByRole("link", { name: app.nav.chat })).toHaveAttribute("href", "/vi/chat");
    expect(nav.queryByText(app.nav.soon)).toBeNull();
  });

  it("logo dẫn về chat với nhân sự mới và về admin với HR", () => {
    const { unmount } = renderWithSession(<AppShell>x</AppShell>);
    for (const link of screen.getAllByRole("link", { name: viMessages.landing.nav.brand })) {
      expect(link).toHaveAttribute("href", "/vi/chat");
    }
    unmount();

    renderWithSession(<AppShell>x</AppShell>, HR);
    for (const link of screen.getAllByRole("link", { name: viMessages.landing.nav.brand })) {
      expect(link).toHaveAttribute("href", "/vi/admin");
    }
  });

  it("đăng xuất gọi backend rồi chuyển về trang đăng nhập", async () => {
    vi.mocked(authApi.logout).mockResolvedValue();
    renderWithSession(<AppShell>x</AppShell>);

    fireEvent.click(screen.getByRole("button", { name: app.signOut }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(authApi.logout).toHaveBeenCalledTimes(1);
  });

  it("đăng xuất lỗi thì ở lại trang, báo lỗi và cho thử lại", async () => {
    vi.mocked(authApi.logout).mockRejectedValue(new Error("network"));
    renderWithSession(<AppShell>x</AppShell>);

    fireEvent.click(screen.getByRole("button", { name: app.signOut }));

    expect(await screen.findByRole("alert")).toHaveTextContent(app.signOutFailed);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: app.signOut })).toBeEnabled();
  });

  it("chuyển sáng/tối, áp dụng lên khung và nhớ lựa chọn", () => {
    const { container } = renderWithSession(<AppShell>x</AppShell>);
    const shell = container.firstElementChild as HTMLElement;
    expect(shell).toHaveAttribute("data-theme", "light");

    fireEvent.click(screen.getByRole("button", { name: app.darkMode }));

    expect(shell).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem("vsf-theme")).toBe("dark");
    expect(screen.getByRole("button", { name: app.lightMode })).toBeInTheDocument();
  });

  it("nhớ giao diện tối từ lần trước", () => {
    window.localStorage.setItem("vsf-theme", "dark");
    const { container } = renderWithSession(<AppShell>x</AppShell>);

    expect(container.firstElementChild).toHaveAttribute("data-theme", "dark");
  });

  it("ngăn kéo trên điện thoại mở bằng nút menu và đóng bằng Escape", () => {
    renderWithSession(<AppShell>x</AppShell>);
    const menu = screen.getByRole("button", { name: app.openMenu });
    expect(menu).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(document, { key: "Escape" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
  });
});

describe("SessionProvider", () => {
  it("phiên bị thu hồi (refresh trả null) thì chuyển về đăng nhập", async () => {
    vi.useFakeTimers();
    vi.mocked(authApi.refresh).mockResolvedValue(null);
    renderWithSession(<AppShell>x</AppShell>);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    });

    expect(replace).toHaveBeenCalledWith("/login");
  });

  it("lỗi mạng khi gia hạn thì giữ nguyên phiên", async () => {
    vi.useFakeTimers();
    vi.mocked(authApi.refresh).mockRejectedValue(new Error("network"));
    renderWithSession(<AppShell>x</AppShell>);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    });

    expect(replace).not.toHaveBeenCalled();
  });
});

describe("ChatShell", () => {
  it("trạng thái đầu: lời chào theo tên, ghi chú minh họa, 4 thẻ gợi ý, ô nhập trống và nút gửi khóa", () => {
    renderWithSession(<ChatShell />);

    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(USER.display_name);
    expect(screen.getByRole("note")).toHaveTextContent(chat.demoNotice);
    expect(within(screen.getByRole("group", { name: chat.suggestionsLabel })).getAllByRole("button")).toHaveLength(4);
    expect(screen.getByRole("button", { name: chat.send })).toBeDisabled();
    expect(screen.queryByRole("button", { name: chat.newConversation })).toBeNull();
  });

  it("bấm thẻ gợi ý: hiện câu hỏi và trạng thái đang tìm, rồi câu trả lời kèm nguồn; bấm nguồn mở trích đoạn", () => {
    vi.useFakeTimers();
    renderWithSession(<ChatShell />);
    const s = chat.suggestions.firstDay;

    fireEvent.click(screen.getByRole("button", { name: new RegExp(s.title) }));

    expect(screen.getByText(s.question)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(chat.checking);
    expect(screen.queryByText(s.answer)).toBeNull();

    act(() => {
      vi.advanceTimersByTime(MOCK_DELAY_MS);
    });

    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByText(s.answer)).toBeInTheDocument();
    expect(screen.queryByText(s.excerpt, { exact: false })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: s.source }));

    expect(screen.getByText(s.excerpt, { exact: false })).toBeInTheDocument();
  });

  it("câu hỏi tự gõ nhận lời nói thẳng là chưa có nguồn, không bịa", () => {
    vi.useFakeTimers();
    renderWithSession(<ChatShell />);

    fireEvent.change(screen.getByLabelText(chat.inputLabel), { target: { value: "Lương tháng này bao nhiêu?" } });
    fireEvent.click(screen.getByRole("button", { name: chat.send }));
    act(() => {
      vi.advanceTimersByTime(MOCK_DELAY_MS);
    });

    expect(screen.getByText("Lương tháng này bao nhiêu?")).toBeInTheDocument();
    expect(screen.getByText(chat.noSource)).toBeInTheDocument();
    expect(screen.queryByText(chat.sourceLabel)).toBeNull();
  });

  it("Enter gửi câu hỏi; Shift+Enter không gửi", () => {
    vi.useFakeTimers();
    renderWithSession(<ChatShell />);
    const input = screen.getByLabelText(chat.inputLabel);

    fireEvent.change(input, { target: { value: "Xin chào" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(screen.queryByRole("status")).toBeNull();

    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("đang chờ trả lời thì không gửi thêm được", () => {
    vi.useFakeTimers();
    renderWithSession(<ChatShell />);

    fireEvent.click(screen.getByRole("button", { name: new RegExp(chat.suggestions.leave.title) }));

    fireEvent.change(screen.getByLabelText(chat.inputLabel), { target: { value: "câu tiếp theo" } });
    expect(screen.getByRole("button", { name: chat.send })).toBeDisabled();
  });

  it("cuộc trò chuyện mới xóa hội thoại và quay về màn chào", () => {
    vi.useFakeTimers();
    renderWithSession(<ChatShell />);
    fireEvent.click(screen.getByRole("button", { name: new RegExp(chat.suggestions.contact.title) }));
    act(() => {
      vi.advanceTimersByTime(MOCK_DELAY_MS);
    });

    fireEvent.click(screen.getByRole("button", { name: chat.newConversation }));

    expect(screen.queryByText(chat.suggestions.contact.answer)).toBeNull();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(USER.display_name);
  });
});

describe("AdminPlaceholder", () => {
  it("hiện lời chào, vai trò HR và đường về trang chat", () => {
    renderWithSession(<AdminPlaceholder />, HR);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("HR Demo 1");
    expect(screen.getByText(app.roles.HR)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: viMessages.admin.openChat })).toHaveAttribute("href", "/vi/chat");
  });
});
