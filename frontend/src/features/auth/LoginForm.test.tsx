import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { LoginForm } from "./LoginForm";
import { SessionError, authApi } from "./session";

const replace = vi.fn();
let nextParam: string | null = null;

vi.mock("@/i18n/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("next/navigation", () => ({ useSearchParams: () => ({ get: () => nextParam }) }));

const login = viMessages.login;
const EXPIRES = "2026-09-21T09:22:03Z";

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText(login.fields.email), { target: { value: email } });
  fireEvent.change(screen.getByLabelText(login.fields.password), { target: { value: password } });
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: login.submit }));
}

beforeEach(() => {
  replace.mockReset();
  nextParam = null;
  vi.restoreAllMocks();
});

describe("LoginForm", () => {
  it("có ô email và mật khẩu với autoComplete đúng để trình quản lý mật khẩu hoạt động", () => {
    render(<LoginForm />);

    expect(screen.getByLabelText(login.fields.email)).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText(login.fields.password)).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByLabelText(login.fields.password)).toHaveAttribute("type", "password");
  });

  it("nút con mắt hiện và ẩn mật khẩu", () => {
    render(<LoginForm />);

    const input = screen.getByLabelText(login.fields.password);
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: login.showPassword }));
    expect(input).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: login.hidePassword }));
    expect(input).toHaveAttribute("type", "password");
  });

  it.each([
    ["", "pw", login.errors.emailRequired],
    ["khong-phai-email", "pw", login.errors.emailInvalid],
    ["a@b.co", "", login.errors.passwordRequired],
  ])("kiểm nhập liệu ở client (%j, %j) và không gọi API", (email, password, message) => {
    const loginSpy = vi.spyOn(authApi, "login");
    render(<LoginForm />);

    fill(email, password);
    submit();

    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(loginSpy).not.toHaveBeenCalled();
  });

  it("thành công: chuyển tới trang mặc định theo vai trò", async () => {
    vi.spyOn(authApi, "login").mockResolvedValue({
      id: 1,
      email: "a@b.co",
      display_name: "A",
      role: "USER",
      department: null,
      expires_at: EXPIRES,
    });
    render(<LoginForm />);

    fill("a@b.co", "pw");
    submit();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/me"));
  });

  it("thành công: nhận ?next= nội bộ, bỏ ?next= độc hại", async () => {
    const spy = vi
      .spyOn(authApi, "login")
      .mockResolvedValue({ id: 1, email: "a@b.co", display_name: "A", role: "HR", department: null, expires_at: EXPIRES });
    nextParam = "/admin/documents";
    const first = render(<LoginForm />);
    fill("a@b.co", "pw");
    submit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin/documents"));
    first.unmount();

    replace.mockReset();
    nextParam = "//evil.com";
    render(<LoginForm />);
    fill("a@b.co", "pw");
    submit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin"));
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it.each([
    ["invalid_credentials", login.errors.invalid],
    ["account_inactive", login.errors.inactive],
    ["rate_limited", login.errors.tooMany],
    ["unavailable", login.errors.unavailable],
    ["network", login.errors.unavailable],
  ] as const)("lỗi từ server %s hiện đúng thông báo và không chuyển trang", async (code, message) => {
    vi.spyOn(authApi, "login").mockRejectedValue(new SessionError(code));
    render(<LoginForm />);

    fill("a@b.co", "pw");
    submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: login.submit })).toBeEnabled();
  });

  it("đang gửi: khóa nút và các ô, hiện chữ đang đăng nhập", async () => {
    vi.spyOn(authApi, "login").mockReturnValue(new Promise(() => {}));
    render(<LoginForm />);

    fill("a@b.co", "pw");
    submit();

    const button = await screen.findByRole("button", { name: login.submitting });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.getByLabelText(login.fields.email)).toBeDisabled();
  });
});
