import { describe, expect, it } from "vitest";

import { isLocale, localeFromPathname, routing, stripLocale } from "./routing";

describe("routing", () => {
  it("chỉ có tiếng Việt và mặc định là vi", () => {
    expect(routing.locales).toEqual(["vi"]);
    expect(routing.defaultLocale).toBe("vi");
  });

  it("nhận diện ngôn ngữ hợp lệ", () => {
    expect(isLocale("vi")).toBe(true);
    expect(isLocale("en")).toBe(false);
    expect(isLocale("")).toBe(false);
  });

  it("lấy ngôn ngữ từ đường dẫn", () => {
    expect(localeFromPathname("/vi/login")).toBe("vi");
    expect(localeFromPathname("/login")).toBeNull();
    expect(localeFromPathname("/")).toBeNull();
  });

  it("bỏ tiền tố ngôn ngữ khỏi đường dẫn", () => {
    expect(stripLocale("/vi/login")).toBe("/login");
    expect(stripLocale("/vi")).toBe("/");
    expect(stripLocale("/login")).toBe("/login");
    expect(stripLocale("")).toBe("/");
  });
});
