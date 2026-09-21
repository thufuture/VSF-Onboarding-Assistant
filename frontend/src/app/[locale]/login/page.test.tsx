import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

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
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => ({ get: () => null }) }));

const login = viMessages.login;

describe("LoginPage", () => {
  it("hiển thị tiêu đề, form, nhãn bản demo và đường về trang chủ", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(login.title);
    expect(screen.getByLabelText(login.fields.email)).toBeInTheDocument();
    expect(screen.getByLabelText(login.fields.password)).toBeInTheDocument();
    expect(screen.getByText(login.demoBadge)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: login.back })).toHaveAttribute("href", "/vi");
  });

  it("panel trái nêu ba nguyên tắc", () => {
    render(<LoginPage />);

    for (const item of Object.values(login.panel.items)) {
      expect(screen.getByRole("heading", { name: item.title })).toBeInTheDocument();
    }
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

  it("không có mã màu hex cứng, không có dấu vết của Ralion hay cơ chế định danh qua header", () => {
    for (const file of files) {
      const code = stripComments(readFileSync(file, "utf8"));
      expect(code, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(code, file).not.toMatch(/ralion|X-User-Id|LanguageSwitcher|localStorage/i);
    }
  });
});
