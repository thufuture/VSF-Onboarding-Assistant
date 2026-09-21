import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionError, authApi } from "./session";

const USER = {
  id: 1,
  email: "hr1@vsf-demo.example",
  display_name: "HR Demo 1",
  role: "HR",
  expires_at: "2026-09-21T09:22:03Z",
} as const;

function mockFetch(implementation: () => Promise<Response>) {
  const fetchMock = vi.fn(implementation);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("authApi.login", () => {
  it("gửi POST JSON kèm cookie và không có header định danh tự chế", async () => {
    const fetchMock = mockFetch(async () => new Response(JSON.stringify(USER), { status: 200 }));

    await expect(authApi.login("hr1@vsf-demo.example", "pw")).resolves.toEqual(USER);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/login");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(String(init.body))).toEqual({ email: "hr1@vsf-demo.example", password: "pw" });
    const headers = Object.keys(init.headers as Record<string, string>).map((name) => name.toLowerCase());
    expect(headers).toEqual(["content-type"]);
  });

  it.each([
    [401, "invalid_credentials"],
    [403, "unavailable"], // 403 không kèm mã ACCOUNT_INACTIVE
    [429, "rate_limited"],
    [404, "unavailable"],
    [500, "unavailable"],
  ])("HTTP %i được đổi thành mã lỗi %s", async (status, code) => {
    mockFetch(async () => new Response("{}", { status }));

    await expect(authApi.login("a@b.co", "pw")).rejects.toMatchObject({ name: "SessionError", code });
  });

  it("403 kèm mã ACCOUNT_INACTIVE là tài khoản bị khóa", async () => {
    const body = { code: "ACCOUNT_INACTIVE", message_key: "auth.account_inactive", detail: null };
    mockFetch(async () => new Response(JSON.stringify(body), { status: 403 }));

    await expect(authApi.login("a@b.co", "pw")).rejects.toMatchObject({ code: "account_inactive" });
  });

  it("lỗi mạng được đổi thành mã network", async () => {
    mockFetch(async () => {
      throw new TypeError("Failed to fetch");
    });

    const error = await authApi.login("a@b.co", "pw").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(SessionError);
    expect(error).toMatchObject({ code: "network" });
  });

  it("phản hồi 200 nhưng không phải JSON được coi là không khả dụng", async () => {
    mockFetch(async () => new Response("<html>", { status: 200 }));

    await expect(authApi.login("a@b.co", "pw")).rejects.toMatchObject({ code: "unavailable" });
  });
});

describe("authApi.me và refresh", () => {
  it("me trả hồ sơ khi 200 và gửi cookie", async () => {
    const fetchMock = mockFetch(async () => new Response(JSON.stringify(USER), { status: 200 }));

    await expect(authApi.me()).resolves.toEqual(USER);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/me");
    expect(init.credentials).toBe("include");
  });

  it.each([["me"], ["refresh"]] as const)("%s trả null khi 401 (chưa đăng nhập)", async (name) => {
    mockFetch(async () => new Response("{}", { status: 401 }));

    await expect(authApi[name]()).resolves.toBeNull();
  });

  it.each([["me"], ["refresh"]] as const)("%s báo lỗi khi 500 hoặc mất mạng", async (name) => {
    mockFetch(async () => new Response("{}", { status: 500 }));
    await expect(authApi[name]()).rejects.toMatchObject({ code: "unavailable" });

    mockFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(authApi[name]()).rejects.toMatchObject({ code: "network" });
  });

  it("refresh dùng POST", async () => {
    const fetchMock = mockFetch(async () => new Response(JSON.stringify(USER), { status: 200 }));

    await authApi.refresh();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/refresh");
    expect(init.method).toBe("POST");
  });
});

describe("authApi.logout", () => {
  it("gửi POST kèm cookie và thành công khi 204", async () => {
    const fetchMock = mockFetch(async () => new Response(null, { status: 204 }));

    await expect(authApi.logout()).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/logout");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
  });

  it("báo lỗi khi backend lỗi hoặc mất mạng để giao diện không giả vờ đã đăng xuất", async () => {
    mockFetch(async () => new Response("{}", { status: 500 }));
    await expect(authApi.logout()).rejects.toMatchObject({ code: "unavailable" });

    mockFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(authApi.logout()).rejects.toMatchObject({ code: "network" });
  });
});
