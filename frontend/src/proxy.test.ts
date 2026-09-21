// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "./proxy";

const request = (path: string) => new NextRequest(`http://localhost:3000${path}`);

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
