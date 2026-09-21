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

describe("HomePage (landing)", () => {
  it("ghép đủ các phần: điều hướng, nội dung chính, chân trang", () => {
    render(<HomePage />);

    expect(screen.getByRole("navigation", { name: viMessages.landing.nav.label })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("có một h1 là tiêu đề hero và nhãn bản demo", () => {
    render(<HomePage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(viMessages.landing.hero.title);
    expect(screen.getByText(viMessages.landing.hero.demoBadge)).toBeInTheDocument();
  });

  it("nút 'Bắt đầu hỏi' và 'Đăng nhập' dẫn tới trang đăng nhập", () => {
    render(<HomePage />);

    expect(screen.getByRole("link", { name: viMessages.landing.hero.primary })).toHaveAttribute("href", "/vi/login");
    expect(screen.getByRole("link", { name: viMessages.landing.nav.login })).toHaveAttribute("href", "/vi/login");
  });

  it("có liên kết 'Bỏ qua tới nội dung' trỏ tới vùng main", () => {
    render(<HomePage />);

    expect(screen.getByRole("link", { name: viMessages.landing.skipLink })).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
  });
});
