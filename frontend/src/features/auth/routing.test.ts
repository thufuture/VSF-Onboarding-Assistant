import { describe, expect, it } from "vitest";

import { defaultLandingPath, internalPath, resolvePostLoginPath } from "./routing";

describe("internalPath (chống chuyển hướng mở)", () => {
  it.each(["/chat", "/chat?q=1", "/admin/documents#top", "/vi/chat"])("nhận đường dẫn nội bộ %s", (value) => {
    expect(internalPath(value)).not.toBeNull();
  });

  it("bỏ tiền tố ngôn ngữ", () => {
    expect(internalPath("/vi/chat?x=1")).toBe("/chat?x=1");
  });

  it.each([
    "//evil.com",
    "/\\evil.com",
    "/\t/evil.com",
    "/\n/evil.com",
    "https://evil.com",
    "http://evil.com/chat",
    "javascript:alert(1)",
    "evil.com",
    "",
    null,
    undefined,
  ])("loại %j", (value) => {
    expect(internalPath(value)).toBeNull();
  });
});

describe("resolvePostLoginPath", () => {
  it("nhân viên vào chat, HR và Admin vào khu quản trị khi không có ?next=", () => {
    expect(defaultLandingPath("USER")).toBe("/chat");
    expect(resolvePostLoginPath("USER", null)).toBe("/chat");
    expect(resolvePostLoginPath("HR", null)).toBe("/admin");
    expect(resolvePostLoginPath("ADMIN", null)).toBe("/admin");
  });

  it("nhận ?next= nội bộ hợp lệ", () => {
    expect(resolvePostLoginPath("USER", "/chat?x=1")).toBe("/chat?x=1");
    expect(resolvePostLoginPath("HR", "/admin/documents")).toBe("/admin/documents");
  });

  it("nhân viên không được đưa vào khu quản trị bằng ?next=", () => {
    expect(resolvePostLoginPath("USER", "/admin")).toBe("/chat");
    expect(resolvePostLoginPath("USER", "/admin/users")).toBe("/chat");
  });

  it("không quay lại trang đăng nhập", () => {
    expect(resolvePostLoginPath("USER", "/login")).toBe("/chat");
    expect(resolvePostLoginPath("HR", "/vi/login")).toBe("/admin");
  });

  it.each(["//evil.com", "/\\evil.com", "https://evil.com", "javascript:alert(1)"])(
    "?next= độc hại %s rơi về trang mặc định theo vai trò",
    (value) => {
      expect(resolvePostLoginPath("USER", value)).toBe("/chat");
      expect(resolvePostLoginPath("HR", value)).toBe("/admin");
    },
  );
});
