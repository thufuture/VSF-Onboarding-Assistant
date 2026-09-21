import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../../messages/vi.json";
import LoginPage from "./page";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href === "/" ? "" : href}`} className={className}>
      {children}
    </a>
  ),
}));

describe("LoginPage (trang khung)", () => {
  it("hiển thị tiêu đề, ghi chú và đường về trang chủ", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(viMessages.login.title);
    expect(screen.getByText(viMessages.login.placeholder)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: viMessages.login.back })).toHaveAttribute("href", "/vi");
  });
});
