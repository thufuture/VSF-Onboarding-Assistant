import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import type { ImgHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { LandingPage } from "./LandingPage";

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    href,
    children,
    className,
    ...rest
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    onClick?: () => void;
    "aria-current"?: "page";
  }) => (
    <a href={`/vi${href === "/" ? "" : href}`} className={className} {...rest}>
      {children}
    </a>
  ),
}));

// next/image cần cấu hình loader khi chạy thật; ở test chỉ cần thẻ img với đúng nguồn và chữ mô tả.
vi.mock("next/image", () => ({
  default: ({ src, alt, className }: ImgHTMLAttributes<HTMLImageElement> & { src: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} className={className} />
  ),
}));

const landing = viMessages.landing;
const ROOT = join(__dirname, "..", "..", "..");

function leaves(node: unknown, prefix = ""): [string, string][] {
  if (typeof node === "string") return [[prefix, node]];
  if (!node || typeof node !== "object") return [];
  return Object.entries(node as Record<string, unknown>).flatMap(([key, value]) =>
    leaves(value, prefix ? `${prefix}.${key}` : key),
  );
}

describe("LandingPage: cấu trúc", () => {
  it("có điều hướng, vùng nội dung chính và chân trang", () => {
    render(<LandingPage />);

    expect(screen.getByRole("navigation", { name: landing.nav.label })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: landing.skipLink })).toHaveAttribute("href", "#main");
  });

  it("có đúng một h1 gồm hai dòng tiêu đề hero", () => {
    render(<LandingPage />);

    const h1 = screen.getByRole("heading", { level: 1 });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(h1).toHaveTextContent(landing.hero.line1);
    expect(h1).toHaveTextContent(landing.hero.line2);
  });

  it("các liên kết neo có đích tồn tại", () => {
    const { container } = render(<LandingPage />);

    for (const id of ["hero", "how", "roles"]) {
      expect(container.querySelector(`#${id}`), `thiếu #${id}`).not.toBeNull();
    }
    const nav = within(screen.getByRole("navigation", { name: landing.nav.label }));
    expect(nav.getByRole("link", { name: landing.nav.how })).toHaveAttribute("href", "#how");
    expect(nav.getByRole("link", { name: landing.nav.roles })).toHaveAttribute("href", "#roles");
  });

  it("header ở trạng thái trong suốt khi đang ở đầu trang", () => {
    const { container } = render(<LandingPage />);

    expect(container.querySelector("header")?.className).toMatch(/headerTop/);
  });
});

describe("LandingPage: hero", () => {
  it("nút chính và nút Đăng nhập dẫn tới trang đăng nhập; nút phụ cuộn tới #how", () => {
    const { container } = render(<LandingPage />);

    const hero = within(container.querySelector("#hero") as HTMLElement);
    const nav = within(screen.getByRole("navigation", { name: landing.nav.label }));
    expect(hero.getByRole("link", { name: landing.hero.primary })).toHaveAttribute("href", "/vi/login");
    expect(nav.getByRole("link", { name: landing.nav.login })).toHaveAttribute("href", "/vi/login");
    expect(hero.getByRole("link", { name: landing.hero.secondary })).toHaveAttribute("href", "#how");
  });

  it("dùng ảnh Vincom Center Đồng Khởi, có chữ mô tả, ghi công tác giả và giấy phép", () => {
    render(<LandingPage />);

    const photo = screen.getByRole("img", { name: landing.hero.photoAlt });
    expect(photo).toHaveAttribute("src", "/images/landing/hero-vincom-dong-khoi.webp");
    expect(screen.getByRole("link", { name: landing.hero.creditAuthor })).toHaveAttribute(
      "href",
      expect.stringContaining("commons.wikimedia.org/wiki/File:Ho_Chi_Minh_City,_Vincom_Center"),
    );
    expect(screen.getByRole("link", { name: landing.hero.creditLicense })).toHaveAttribute(
      "href",
      "https://creativecommons.org/licenses/by-sa/4.0/",
    );
    expect(screen.getByText(new RegExp(landing.hero.creditLead))).toBeInTheDocument();
  });

  it("có nhãn bản demo và hai cam kết", () => {
    const { container } = render(<LandingPage />);

    const hero = within(container.querySelector("#hero") as HTMLElement);
    expect(hero.getByText(landing.hero.badge)).toBeInTheDocument();
    expect(hero.getByText(landing.hero.checkSources)).toBeInTheDocument();
    expect(hero.getByText(landing.hero.checkProcess)).toBeInTheDocument();
  });

  it("tệp ảnh có thật và được ghi công trong CREDITS.md", () => {
    expect(existsSync(join(ROOT, "public", "images", "landing", "hero-vincom-dong-khoi.webp"))).toBe(true);
    const credits = readFileSync(join(ROOT, "public", "images", "landing", "CREDITS.md"), "utf8");
    expect(credits).toContain("hero-vincom-dong-khoi.webp");
    expect(credits).toContain("CC BY-SA 4.0");
    expect(credits).toContain("Steffen Schmitz");
  });
});

describe("LandingPage: nội dung", () => {
  it("có dịch vụ, tính năng, vai trò và công nghệ", () => {
    render(<LandingPage />);

    for (const service of Object.values(landing.services)) {
      expect(screen.getAllByText(service.title).length).toBeGreaterThan(0);
    }
    for (const feature of Object.values(landing.features)) {
      expect(screen.getAllByText(feature.label).length).toBeGreaterThan(0);
    }
    for (const role of ["asker", "hr", "team", "admin"] as const) {
      const heading = screen.getByRole("heading", { name: landing.roles[role].title });
      expect(within(heading.closest("article") as HTMLElement).getByRole("link")).toHaveAttribute("href", "/vi/login");
    }
    for (const key of ["web", "api", "db", "search", "embed", "llm", "docker"] as const) {
      expect(screen.getByText(landing.tech[key].name)).toBeInTheDocument();
    }
  });

  it("mockup dùng dữ liệu mẫu có thật trong bộ seed và ghi rõ là minh họa", () => {
    render(<LandingPage />);

    expect(screen.getByText(new RegExp(landing.mock.process.s1.label))).toBeInTheDocument();
    expect(screen.getByText(landing.mock.ticket.k1.value)).toBeInTheDocument();
    expect(screen.getByText(landing.mock.sample)).toBeInTheDocument();
  });

  it("nút kêu gọi cuối trang dẫn tới trang đăng nhập", () => {
    render(<LandingPage />);

    const section = screen.getByRole("heading", { name: landing.cta.heading }).closest("section") as HTMLElement;
    expect(within(section).getByRole("link")).toHaveAttribute("href", "/vi/login");
  });
});

describe("LandingPage: quy tắc nội dung", () => {
  const texts = leaves(landing);

  it("không có số liệu hiệu quả chưa đo, không nhắc VLearn, VinUni hay Ralion", () => {
    for (const [key, value] of texts) {
      expect(value, key).not.toMatch(/\d+\s*%/);
      expect(value, key).not.toMatch(/vlearn|vinuni|ralion/i);
    }
  });

  it("chỉ phần chú thích ảnh minh họa mới nhắc Vincom Đồng Khởi, và ghi rõ là ảnh minh họa", () => {
    for (const [key, value] of texts) {
      if (key === "hero.photoAlt" || key === "hero.creditLead") continue;
      expect(value, key).not.toMatch(/vincom|đồng khởi/i);
    }
    expect(landing.hero.creditLead).toMatch(/Ảnh minh họa/);
  });

  it("không có chữ tiếng Việt nằm cứng trong component (chữ phải ở messages/vi.json)", () => {
    const vietnamese = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
    const files = [join(__dirname, "LandingPage.tsx"), join(ROOT, "src", "components", "brand", "VsfBrand.tsx")];
    for (const file of files) {
      const code = readFileSync(file, "utf8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .split("\n")
        .map((line) => line.replace(/(^|\s)\/\/.*$/, ""))
        .join("\n");
      expect(code, file).not.toMatch(vietnamese);
    }
  });
});
