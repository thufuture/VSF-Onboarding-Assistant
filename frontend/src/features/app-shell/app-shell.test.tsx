import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { ChatShell } from "@/features/chat/ChatShell";
import { SessionProvider } from "@/features/auth/SessionProvider";
import type { SessionUserResponseDTO } from "@/features/auth/dto/responseDTO/auth.response";
import { authApi } from "@/features/auth/session";

import { AdminPlaceholder } from "./AdminPlaceholder";
import { AppHeader } from "./AppHeader";

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

import { NextIntlClientProvider } from "next-intl";

const USER: SessionUserResponseDTO = {
  id: 7,
  email: "user1@vsf-demo.example",
  display_name: "Nguyễn Văn A",
  role: "USER",
  expires_at: "2026-09-21T10:00:00Z",
};

function renderWithSession(ui: ReactNode, user: SessionUserResponseDTO = USER) {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <SessionProvider initialUser={user}>{ui}</SessionProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  replace.mockReset();
  vi.mocked(authApi.logout).mockReset();
  vi.mocked(authApi.refresh).mockReset();
});
afterEach(() => vi.useRealTimers());

describe("AppHeader", () => {
  it("hiện tên và vai trò của người dùng", () => {
    renderWithSession(<AppHeader />);

    expect(screen.getByText(USER.display_name)).toBeInTheDocument();
    expect(screen.getByText(viMessages.app.roles.USER)).toBeInTheDocument();
  });

  it("đăng xuất gọi backend rồi chuyển về trang đăng nhập", async () => {
    vi.mocked(authApi.logout).mockResolvedValue();
    renderWithSession(<AppHeader />);

    fireEvent.click(screen.getByRole("button", { name: viMessages.app.signOut }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(authApi.logout).toHaveBeenCalledTimes(1);
  });

  it("đăng xuất lỗi thì ở lại trang, báo lỗi và cho thử lại", async () => {
    vi.mocked(authApi.logout).mockRejectedValue(new Error("network"));
    renderWithSession(<AppHeader />);

    fireEvent.click(screen.getByRole("button", { name: viMessages.app.signOut }));

    expect(await screen.findByRole("alert")).toHaveTextContent(viMessages.app.signOutFailed);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: viMessages.app.signOut })).toBeEnabled();
  });

  it("logo dẫn về chat với nhân sự mới và về admin với HR", () => {
    const { unmount } = renderWithSession(<AppHeader />);
    expect(screen.getByRole("link", { name: viMessages.landing.nav.brand })).toHaveAttribute("href", "/vi/chat");
    unmount();

    renderWithSession(<AppHeader />, { ...USER, role: "HR" });
    expect(screen.getByRole("link", { name: viMessages.landing.nav.brand })).toHaveAttribute("href", "/vi/admin");
  });
});

describe("SessionProvider", () => {
  it("phiên bị thu hồi (refresh trả null) thì chuyển về đăng nhập", async () => {
    vi.useFakeTimers();
    vi.mocked(authApi.refresh).mockResolvedValue(null);
    renderWithSession(<AppHeader />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    });

    expect(replace).toHaveBeenCalledWith("/login");
  });

  it("lỗi mạng khi gia hạn thì giữ nguyên phiên", async () => {
    vi.useFakeTimers();
    vi.mocked(authApi.refresh).mockRejectedValue(new Error("network"));
    renderWithSession(<AppHeader />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    });

    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText(USER.display_name)).toBeInTheDocument();
  });
});

describe("ChatShell", () => {
  it("chào đúng tên và có ghi chú nội dung minh họa", () => {
    renderWithSession(<ChatShell />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(USER.display_name);
    expect(screen.getByRole("note")).toHaveTextContent(viMessages.chat.demoNotice);
  });

  it("bấm câu hỏi gợi ý hiện câu trả lời kèm khối Nguồn", async () => {
    renderWithSession(<ChatShell />);
    const s = viMessages.chat.suggestions.firstDay;

    fireEvent.click(screen.getByRole("button", { name: s.question }));

    expect(screen.getByText(s.answer)).toBeInTheDocument();
    expect(screen.getByText(s.source)).toBeInTheDocument();
  });

  it("câu hỏi tự gõ nhận lời nói thẳng là chưa có nguồn, không bịa", async () => {
    renderWithSession(<ChatShell />);

    fireEvent.change(screen.getByLabelText(viMessages.chat.inputLabel), { target: { value: "Lương tháng này bao nhiêu?" } });
    fireEvent.click(screen.getByRole("button", { name: viMessages.chat.send }));

    expect(screen.getByText("Lương tháng này bao nhiêu?")).toBeInTheDocument();
    expect(screen.getByText(viMessages.chat.noSource)).toBeInTheDocument();
    expect(screen.queryByText(viMessages.chat.sourceLabel)).toBeNull();
  });

  it("nút gửi bị khóa khi ô nhập trống", () => {
    renderWithSession(<ChatShell />);

    expect(screen.getByRole("button", { name: viMessages.chat.send })).toBeDisabled();
  });
});

describe("AdminPlaceholder", () => {
  it("hiện lời chào, vai trò HR và đường về trang chat", () => {
    renderWithSession(<AdminPlaceholder />, { ...USER, role: "HR", display_name: "HR Demo 1" });

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("HR Demo 1");
    expect(screen.getByText(viMessages.app.roles.HR)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: viMessages.admin.openChat })).toHaveAttribute("href", "/vi/chat");
  });
});
