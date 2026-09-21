import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { FEATURE_KEYS, FeatureCards } from "./FeatureCards";
import { Footer } from "./Footer";
import { Hero } from "./Hero";
import { Navbar } from "./Navbar";
import { STEP_KEYS, Steps } from "./Steps";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={`/vi${href === "/" ? "" : href}`} className={className}>
      {children}
    </a>
  ),
}));

const landing = viMessages.landing;

describe("Navbar", () => {
  it("có thương hiệu, hai liên kết neo và nút đăng nhập", () => {
    render(<Navbar />);

    expect(screen.getByRole("link", { name: landing.nav.brand })).toHaveAttribute("href", "/vi");
    expect(screen.getByRole("link", { name: landing.nav.how })).toHaveAttribute("href", "#how");
    expect(screen.getByRole("link", { name: landing.nav.features })).toHaveAttribute("href", "#features");
    expect(screen.getByRole("link", { name: landing.nav.login })).toHaveAttribute("href", "/vi/login");
  });
});

describe("Hero", () => {
  it("nút phụ cuộn tới mục 'Cách hoạt động'", () => {
    render(<Hero />);

    expect(screen.getByRole("link", { name: landing.hero.secondary })).toHaveAttribute("href", "#how");
    expect(screen.getByText(landing.hero.note)).toBeInTheDocument();
  });

  it("không nêu tên công ty như trang chính thức và có nhãn bản demo", () => {
    render(<Hero />);

    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).not.toMatch(/vingroup|vinsmart|vsf/i);
    expect(screen.getByText(landing.hero.demoBadge)).toBeInTheDocument();
  });
});

describe("Steps", () => {
  it("hiển thị năm bước theo thứ tự trong danh sách có số", () => {
    render(<Steps />);

    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    STEP_KEYS.forEach((key, index) => {
      expect(items[index]).toHaveTextContent(landing.steps.items[key].title);
      expect(items[index]).toHaveTextContent(landing.steps.items[key].body);
    });
  });

  it("là đích của liên kết neo #how", () => {
    const { container } = render(<Steps />);

    expect(container.querySelector("#how")).not.toBeNull();
  });
});

describe("FeatureCards", () => {
  it("hiển thị ba thẻ và là đích của liên kết neo #features", () => {
    const { container } = render(<FeatureCards />);

    expect(container.querySelector("#features")).not.toBeNull();
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items).toHaveLength(FEATURE_KEYS.length);
    FEATURE_KEYS.forEach((key, index) => {
      expect(items[index]).toHaveTextContent(landing.features.items[key].title);
    });
  });
});

describe("Footer", () => {
  it("có nhãn bản demo, địa chỉ liên hệ demo và bản quyền", () => {
    render(<Footer />);

    expect(screen.getByText(landing.footer.demo)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: landing.footer.contact })).toHaveAttribute(
      "href",
      `mailto:${landing.footer.contact}`,
    );
    expect(screen.getByText(landing.footer.copyright)).toBeInTheDocument();
  });
});

describe("nội dung", () => {
  const dir = __dirname;
  const sources = readdirSync(dir).filter((name) => name.endsWith(".tsx") && !name.endsWith(".test.tsx"));

  it("không có chữ tiếng Việt nằm cứng trong component (chữ phải ở messages/vi.json)", () => {
    const vietnamese = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
    expect(sources.length).toBeGreaterThan(0);
    for (const name of sources) {
      const code = readFileSync(join(dir, name), "utf8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .split("\n")
        .map((line) => line.replace(/(^|\s)\/\/.*$/, ""))
        .join("\n");
      expect(code, `${name} chứa chữ tiếng Việt cứng`).not.toMatch(vietnamese);
    }
  });

  it("không có số liệu hiệu quả chưa đo và không nhắc VLearn/VinUni", () => {
    const text = JSON.stringify(landing);
    expect(text).not.toMatch(/vlearn|vinuni/i);
    expect(text).not.toMatch(/\d+\s*%/);
  });

  it("không nói hay ngụ ý VSF làm việc ở Vincom Đồng Khởi", () => {
    expect(JSON.stringify(landing)).not.toMatch(/vincom|đồng khởi/i);
  });
});
