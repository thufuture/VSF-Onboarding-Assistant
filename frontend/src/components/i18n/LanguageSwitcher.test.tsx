import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { LanguageSwitcher } from "./LanguageSwitcher";

const replace = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  usePathname: () => "/login",
  useRouter: () => ({ replace }),
}));

const common = viMessages.common;

beforeEach(() => {
  replace.mockReset();
  window.history.replaceState(null, "", "/vi/login");
});

describe("LanguageSwitcher", () => {
  it("hiện ngôn ngữ hiện tại và cả hai lựa chọn bằng tên gốc của từng ngôn ngữ", () => {
    render(<LanguageSwitcher />);

    expect(screen.getByLabelText(`${common.language}: ${common.vietnamese}`)).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Việt Nam/ })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("menuitem", { name: /English/ })).not.toHaveAttribute("aria-current");
  });

  it("chọn English đổi tiền tố ngôn ngữ và giữ nguyên trang", () => {
    render(<LanguageSwitcher />);

    fireEvent.click(screen.getByRole("menuitem", { name: /English/ }));

    expect(replace).toHaveBeenCalledWith("/login", { locale: "en" });
  });

  it("giữ chuỗi truy vấn (ví dụ ?next=) khi đổi ngôn ngữ", () => {
    window.history.replaceState(null, "", "/vi/login?next=%2Fchat");
    render(<LanguageSwitcher />);

    fireEvent.click(screen.getByRole("menuitem", { name: /English/ }));

    expect(replace).toHaveBeenCalledWith("/login?next=%2Fchat", { locale: "en" });
  });

  it("chọn lại ngôn ngữ đang dùng thì không làm gì", () => {
    render(<LanguageSwitcher />);

    fireEvent.click(screen.getByRole("menuitem", { name: /Việt Nam/ }));

    expect(replace).not.toHaveBeenCalled();
  });
});
