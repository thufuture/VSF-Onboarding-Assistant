// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "./proxy";

const request = (path: string, cookie?: string) =>
  new NextRequest(`http://localhost:3000${path}`, cookie ? { headers: { cookie } } : undefined);

describe("proxy", () => {
  it("chuyển / về /vi (307)", () => {
    const response = proxy(request("/"));
    expect(response.status).toBe(307);
    expect(new URL(response.headers.get("location") ?? "").pathname).toBe("/vi");
  });

  it("thêm tiền tố ngôn ngữ cho đường dẫn chưa có", () => {
    const response = proxy(request("/login"));
    expect(response.status).toBe(307);
    expect(new URL(response.headers.get("location") ?? "").pathname).toBe("/vi/login");
  });

  it("giữ nguyên chuỗi truy vấn khi chuyển hướng", () => {
    const response = proxy(request("/login?next=%2Fvi%2Fchat"));
    expect(new URL(response.headers.get("location") ?? "").search).toBe("?next=%2Fvi%2Fchat");
  });

  it("cho đi tiếp đường dẫn đã có ngôn ngữ và gắn header ngôn ngữ", () => {
    const response = proxy(request("/vi/login"));
    expect(response.status).toBe(200);
    expect(response.headers.get("location")).toBeNull();
    expect(response.headers.get("x-middleware-request-x-vsf-locale")).toBe("vi");
  });

  it("cho đi tiếp đường dẫn tiếng Anh và gắn header ngôn ngữ en", () => {
    const response = proxy(request("/en/login"));
    expect(response.status).toBe(200);
    expect(response.headers.get("x-middleware-request-x-vsf-locale")).toBe("en");
  });

  describe("cổng đăng nhập", () => {
    it.each(["/vi/chat", "/vi/admin", "/en/chat", "/vi/admin/documents"])("%s không có cookie bị chuyển về đăng nhập", (path) => {
      const response = proxy(request(path));
      expect(response.status).toBe(307);
      const location = new URL(response.headers.get("location") ?? "");
      expect(location.pathname).toBe(`/${path.split("/")[1]}/login`);
      expect(location.searchParams.get("next")).toBe(path);
    });

    it("giữ chuỗi truy vấn trong next", () => {
      const location = new URL(proxy(request("/vi/chat?q=1")).headers.get("location") ?? "");
      expect(location.searchParams.get("next")).toBe("/vi/chat?q=1");
    });

    it("/chat chưa có ngôn ngữ đi qua bước thêm ngôn ngữ rồi mới tới cổng", () => {
      expect(new URL(proxy(request("/chat")).headers.get("location") ?? "").pathname).toBe("/vi/chat");
    });

    it("có cookie thì cho vào và cấm lưu bộ nhớ đệm", () => {
      const response = proxy(request("/vi/chat", "vsf_session=abc"));
      expect(response.status).toBe(200);
      expect(response.headers.get("cache-control")).toBe("no-store");
    });

    it("trang công khai không bị chặn và không bị cấm bộ nhớ đệm", () => {
      for (const path of ["/vi", "/vi/login", "/en"]) {
        const response = proxy(request(path));
        expect(response.status).toBe(200);
        expect(response.headers.get("cache-control")).toBeNull();
      }
    });

    it("đường dẫn chỉ giống tên khu bảo vệ (/vi/chatbot) không bị chặn", () => {
      expect(proxy(request("/vi/chatbot")).status).toBe(200);
    });
  });

  it("matcher loại trừ /api, tài nguyên Next và tệp có đuôi", async () => {
    const { config } = await import("./proxy");
    const pattern = new RegExp(`^${config.matcher[0].replace(/^\//, "\\/")}$`);
    expect(pattern.test("/vi/login")).toBe(true);
    expect(pattern.test("/api/v1/health")).toBe(false);
    expect(pattern.test("/_next/static/chunk.js")).toBe(false);
    expect(pattern.test("/favicon.ico")).toBe(false);
    expect(pattern.test("/robots.txt")).toBe(false);
  });
});
