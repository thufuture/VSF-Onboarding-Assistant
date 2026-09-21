import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionError, authApi } from "./session";

const USER = { id: 1, email: "hr1@vsf-demo.example", display_name: "HR Demo 1", role: "HR" } as const;

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
    [403, "invalid_credentials"],
    [429, "rate_limited"],
    [404, "unavailable"],
    [500, "unavailable"],
  ])("HTTP %i được đổi thành mã lỗi %s", async (status, code) => {
    mockFetch(async () => new Response("{}", { status }));

    await expect(authApi.login("a@b.co", "pw")).rejects.toMatchObject({ name: "SessionError", code });
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
