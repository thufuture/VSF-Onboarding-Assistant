import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../../messages/vi.json";
import LoginPage from "./page";

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    "aria-label"?: string;
  }) => (
    <a href={`/vi${href === "/" ? "" : href}`} {...rest}>
      {children}
    </a>
  ),
  usePathname: () => "/login",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => ({ get: () => null }) }));
vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}));

const login = viMessages.login;
const nav = viMessages.landing.nav;
const footer = viMessages.landing.footer;

describe("LoginPage", () => {
  it("bên trái có tiêu đề h1 hai dòng, mô tả, ba lợi ích và câu trích; thẻ đăng nhập có h2 và form", () => {
    render(<LoginPage />);

    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent(login.welcomeLine1);
    expect(h1).toHaveTextContent(login.welcomeLine2);
    expect(screen.getByText(login.welcomeDescription)).toBeInTheDocument();
    for (const benefit of Object.values(login.benefits)) {
      expect(screen.getByText(benefit)).toBeInTheDocument();
    }
    expect(screen.getByText(login.quote)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: login.title })).toBeInTheDocument();
    expect(screen.getByLabelText(login.fields.email)).toBeInTheDocument();
    expect(screen.getByLabelText(login.fields.password)).toBeInTheDocument();
  });

  it("dùng ảnh nền toàn khung của landing, có header với logo và chọn ngôn ngữ", () => {
    const { container } = render(<LoginPage />);

    expect(container.querySelector("img[src='/images/landing/hero-vincom-dong-khoi.webp']")).not.toBeNull();
    const header = within(screen.getByRole("navigation", { name: nav.label }));
    expect(header.getByRole("link", { name: nav.brand })).toHaveAttribute("href", "/vi");
    expect(header.getByLabelText(new RegExp(`^${viMessages.common.language}: `))).toBeInTheDocument();
  });

  it("chân thẻ có gợi ý đăng nhập lần đầu (mở ra ghi chú) và nút hỗ trợ; chân trang có bản quyền và đường về trang chủ", () => {
    render(<LoginPage />);

    expect(screen.getByText(login.firstTime)).toBeInTheDocument();
    expect(screen.getByText(login.note)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: login.support })).toHaveAttribute("href", `mailto:${footer.email}`);
    expect(screen.getByText(footer.copyright)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: login.back })).toHaveAttribute("href", "/vi");
  });

  it("không còn nhãn giới thiệu phía trên tiêu đề", () => {
    render(<LoginPage />);

    expect(screen.queryByText("Trợ lý onboarding cho nhân sự mới")).toBeNull();
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
      expect(code, file).not.toMatch(/ralion|X-User-Id|localStorage/i);
    }
  });

  it("SCSS đăng nhập không còn chữ Ralion, video hay liên kết ngoài", () => {
    const scss = readFileSync(join(root, "features", "auth", "LoginPage.module.scss"), "utf8");
    expect(scss).not.toMatch(/ralion|video|https?:\/\//i);
  });
});
