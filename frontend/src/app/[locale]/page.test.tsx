import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import HomePage from "./page";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href === "/" ? "" : href}`} className={className}>
      {children}
    </a>
  ),
}));

describe("HomePage", () => {
  it("hiển thị tên, nhãn bản demo và liên kết tới trang đăng nhập", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(viMessages.home.title);
    expect(screen.getByText(viMessages.home.demoNote)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: viMessages.home.cta })).toHaveAttribute("href", "/vi/login");
  });
});
