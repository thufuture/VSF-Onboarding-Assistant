import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ImgHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { LandingPage } from "./LandingPage";

vi.mock("@/i18n/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace: vi.fn() }),
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
// Khớp tên truy cập được có chứa chuỗi (không dùng RegExp vì tiêu đề có dấu ngoặc như "Nhân sự (HR)").
const includes = (text: string) => (name: string) => name.includes(text);
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

describe("LandingPage: cuộn về đầu trang", () => {
  it.each([
    ["mục Trợ lý làm gì", landing.nav.top],
    ["logo", landing.nav.brand],
  ])("bấm %s cuộn mượt về đầu trang (kể cả khi URL đã có #hero)", (_label, name) => {
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    render(<LandingPage />);

    const nav = within(screen.getByRole("navigation", { name: landing.nav.label }));
    fireEvent.click(nav.getByRole("link", { name }));

    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
    vi.unstubAllGlobals();
  });
});

describe("LandingPage: ngôn ngữ", () => {
  it("header có công tắc ngôn ngữ Việt/Anh", () => {
    render(<LandingPage />);

    const nav = within(screen.getByRole("navigation", { name: landing.nav.label }));
    expect(nav.getByLabelText(new RegExp(`^${viMessages.common.language}: `))).toBeInTheDocument();
    expect(nav.getByRole("menuitem", { name: /English/ })).toBeInTheDocument();
  });
});

describe("LandingPage: logo", () => {
  it("có chữ V, tên VSF Onboarding và chữ Assistant in đậm màu riêng", () => {
    render(<LandingPage />);

    const nav = within(screen.getByRole("navigation", { name: landing.nav.label }));
    const brand = nav.getByRole("link", { name: landing.nav.brand });
    expect(brand.querySelector("svg")).not.toBeNull();
    expect(brand.querySelector("circle")).toBeNull(); // không có chấm đỏ trên biểu tượng
    expect(existsSync(join(ROOT, "src", "app", "icon.svg"))).toBe(true); // biểu tượng trên tab trình duyệt
    expect(within(brand).getByText("VSF Onboarding", { exact: false })).toBeInTheDocument();
    expect(within(brand).getByText("Assistant").className).toMatch(/accent/);
  });
});

describe("LandingPage: công nghệ", () => {
  it("hiển thị đủ tám công nghệ, mỗi cái một logo có thật", () => {
    const { container } = render(<LandingPage />);

    const keys = Object.keys(landing.tech).filter((key) => key !== "title");
    expect(keys).toHaveLength(8);
    const logos = Array.from(container.querySelectorAll("img[src^='/images/tech/']"));
    expect(logos).toHaveLength(8);
    for (const logo of logos) {
      expect(existsSync(join(ROOT, "public", logo.getAttribute("src") as string))).toBe(true);
    }
    for (const key of keys) {
      const item = landing.tech[key as keyof typeof landing.tech] as { name: string };
      expect(screen.getByText(item.name)).toBeInTheDocument();
    }
  });

  it("logo được ghi nguồn và giấy phép trong CREDITS.md", () => {
    const credits = readFileSync(join(ROOT, "public", "images", "tech", "CREDITS.md"), "utf8");
    expect(credits).toMatch(/devicon/i);
    expect(credits).toMatch(/Simple Icons/i);
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

  it("dùng ảnh Vincom Center Đồng Khởi làm nền, có chữ mô tả", () => {
    render(<LandingPage />);

    const photo = screen.getByRole("img", { name: landing.hero.photoAlt });
    expect(photo).toHaveAttribute("src", "/images/landing/hero-vincom-dong-khoi.webp");
  });

  it("ghi công tác giả và giấy phép ảnh ở chân trang (CC BY-SA yêu cầu), không đặt trên ảnh", () => {
    const { container } = render(<LandingPage />);

    const hero = within(container.querySelector("#hero") as HTMLElement);
    expect(hero.queryByRole("link", { name: "Steffen Schmitz" })).toBeNull();
    const footer = within(screen.getByRole("contentinfo"));
    // Ba ảnh, mỗi ảnh một tác giả và một giấy phép.
    for (const author of ["Steffen Schmitz", "trungydang", "pqthong0911"]) {
      expect(footer.getByRole("link", { name: author })).toHaveAttribute(
        "href",
        expect.stringContaining("commons.wikimedia.org/wiki/File:"),
      );
    }
    expect(footer.getByRole("link", { name: "CC BY-SA 4.0" })).toHaveAttribute(
      "href",
      "https://creativecommons.org/licenses/by-sa/4.0/",
    );
    expect(footer.getAllByRole("link", { name: "CC BY 3.0" })).toHaveLength(2);
    expect(footer.getByText(landing.footer.photoEdited, { exact: false })).toBeInTheDocument();
  });

  it("tiêu đề trắng hai dòng, có hai cam kết, không còn nhãn bản demo", () => {
    const { container } = render(<LandingPage />);

    const hero = within(container.querySelector("#hero") as HTMLElement);
    expect(hero.getByRole("heading", { level: 1 })).toHaveTextContent(landing.hero.line2);
    expect(hero.queryByText("Bản demo thực tập")).toBeNull();
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
  });

  it("khối vai trò: thẻ ảnh đổi theo ô hình thoi được chọn, có một nút đăng nhập", () => {
    render(<LandingPage />);

    const section = screen
      .getByRole("heading", { level: 2, name: new RegExp(landing.roles.titleStart) })
      .closest("section") as HTMLElement;
    const roles = within(section);
    // Mặc định hiện vai trò đầu tiên.
    expect(roles.getByRole("heading", { level: 3 })).toHaveTextContent(landing.roles.asker.title);
    expect(roles.getByRole("link", { name: includes(landing.roles.asker.cta) })).toHaveAttribute("href", "/vi/login");
    for (const key of ["asker", "hr", "team", "admin"] as const) {
      expect(roles.getByRole("button", { name: includes(landing.roles[key].title) })).toBeInTheDocument();
    }
    fireEvent.click(roles.getByRole("button", { name: includes(landing.roles.hr.title) }));
    expect(roles.getByRole("heading", { level: 3 })).toHaveTextContent(landing.roles.hr.title);
    expect(roles.getByText(landing.roles.hr.body)).toBeInTheDocument();
    fireEvent.mouseEnter(roles.getByRole("button", { name: includes(landing.roles.admin.title) }));
    expect(roles.getByRole("heading", { level: 3 })).toHaveTextContent(landing.roles.admin.title);
  });

  it("phần kêu gọi có ảnh nền và chân trang có bốn cột", () => {
    const { container } = render(<LandingPage />);

    expect(container.querySelector("img[src='/images/landing/cta-vincom-towers.webp']")).not.toBeNull();
    expect(container.querySelector("img[src='/images/landing/roles-vincom-facade.webp']")).not.toBeNull();
    const footer = within(screen.getByRole("contentinfo"));
    for (const title of [landing.footer.aboutTitle, landing.footer.accessTitle, landing.footer.contactTitle]) {
      expect(footer.getByText(title)).toBeInTheDocument();
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
    expect(within(section).getByRole("link", { name: includes(landing.cta.button) })).toHaveAttribute(
      "href",
      "/vi/login",
    );
  });
});

describe("kiểu dáng", () => {
  function walk(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
      entry.isDirectory() ? walk(join(dir, entry.name)) : [join(dir, entry.name)],
    );
  }

  it("dùng SCSS module: không còn tệp .module.css nào trong src", () => {
    const files = walk(join(ROOT, "src"));
    expect(files.filter((file) => file.endsWith(".module.css"))).toEqual([]);
    expect(files.filter((file) => file.endsWith(".module.scss")).length).toBeGreaterThanOrEqual(5);
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
      if (key === "hero.photoAlt" || key === "footer.photoLead") continue;
      expect(value, key).not.toMatch(/vincom|đồng khởi/i);
    }
    expect(landing.footer.photoLead).toMatch(/ảnh minh họa/i);
  });

  it("không có chữ tiếng Việt nằm cứng trong component (chữ phải ở messages/vi.json)", () => {
    const vietnamese = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
    const files = [
      join(__dirname, "LandingPage.tsx"),
      join(__dirname, "RolesFlow.tsx"),
      join(__dirname, "CtaFooter.tsx"),
      join(ROOT, "src", "components", "brand", "VsfBrand.tsx"),
    ];
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
