import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { render, screen, within } from "@testing-library/react";
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
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => ({ get: () => null }) }));

const login = viMessages.login;
const nav = viMessages.landing.nav;

describe("LoginPage", () => {
  it("panel trái có tiêu đề h1, mô tả và ba lợi ích; thẻ đăng nhập có h2 và form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(login.welcomeTitle);
    expect(screen.getByText(login.welcomeDescription)).toBeInTheDocument();
    for (const benefit of Object.values(login.benefits)) {
      expect(screen.getByText(benefit)).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { level: 2, name: login.title })).toBeInTheDocument();
    expect(screen.getByLabelText(login.fields.email)).toBeInTheDocument();
    expect(screen.getByLabelText(login.fields.password)).toBeInTheDocument();
  });

  it("header có thương hiệu và ba liên kết về landing; có ghi chú bản demo và đường về trang chủ", () => {
    render(<LoginPage />);

    const header = within(screen.getByRole("navigation", { name: nav.label }));
    expect(header.getByRole("link", { name: nav.top })).toHaveAttribute("href", "/vi");
    expect(header.getByRole("link", { name: nav.how })).toHaveAttribute("href", "/vi/#how");
    expect(header.getByRole("link", { name: nav.roles })).toHaveAttribute("href", "/vi/#roles");
    expect(screen.getByText(login.note)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: login.back })).toHaveAttribute("href", "/vi");
  });
});

describe("mã nguồn giao diện đăng nhập", () => {
  const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
  const files = [
    join(root, "app", "[locale]", "login", "page.tsx"),
    ...readdirSync(join(root, "features", "auth"))
      .filter((name) => /\.(ts|tsx)$/.test(name) && !/\.test\./.test(name))
      .map((name) => join(root, "features", "auth", name)),
  ];

  function stripComments(code: string): string {
    return code
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .split("\n")
      .map((line) => line.replace(/(^|\s)\/\/.*$/, ""))
      .join("\n");
  }

  it("không có chữ tiếng Việt nằm cứng (chữ phải ở messages/vi.json)", () => {
    const vietnamese = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
    for (const file of files) {
      expect(stripComments(readFileSync(file, "utf8")), file).not.toMatch(vietnamese);
    }
  });

  it("không có dấu vết của Ralion, cơ chế định danh qua header hay lưu định danh ở trình duyệt", () => {
    for (const file of files) {
      const code = stripComments(readFileSync(file, "utf8"));
      expect(code, file).not.toMatch(/ralion|X-User-Id|LanguageSwitcher|localStorage/i);
    }
  });

  it("CSS đăng nhập không còn chữ Ralion, video hay liên kết ngoài", () => {
    const css = readFileSync(join(root, "features", "auth", "LoginPage.module.css"), "utf8");
    expect(css).not.toMatch(/ralion|video|https?:\/\//i);
  });
});
