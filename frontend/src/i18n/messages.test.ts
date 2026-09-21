import { describe, expect, it } from "vitest";

import en from "../../messages/en.json";
import vi from "../../messages/vi.json";

/** Trả về mọi đường dẫn khóa dạng "a.b.c" của các chuỗi trong catalog. */
function leaves(node: unknown, prefix = ""): [string, string][] {
  if (typeof node === "string") return [[prefix, node]];
  if (!node || typeof node !== "object") return [];
  return Object.entries(node as Record<string, unknown>).flatMap(([key, value]) =>
    leaves(value, prefix ? `${prefix}.${key}` : key),
  );
}

describe("messages/vi.json", () => {
  const all = leaves(vi);

  it("có các khóa mà giao diện khung cần", () => {
    const keys = all.map(([key]) => key);
    for (const required of [
      "metadata.title",
      "metadata.description",
      "landing.skipLink",
      "landing.nav.login",
      "landing.hero.line1",
      "landing.hero.description",
      "landing.hero.primary",
      "landing.footer.photoLead",
      "landing.intro.heading",
      "landing.roles.titleStart",
      "landing.footer.tagline",
      "login.title",
      "login.subtitle",
      "login.submit",
      "login.errors.invalid",
      "login.back",
    ]) {
      expect(keys).toContain(required);
    }
  });

  it("không có chuỗi rỗng", () => {
    for (const [key, value] of all) {
      expect(value.trim(), `khóa ${key} rỗng`).not.toBe("");
    }
  });
});

describe("messages/en.json", () => {
  const viKeys = leaves(vi).map(([key]) => key);
  const enLeaves = leaves(en);

  it("có đúng cùng bộ khóa với vi.json (không thiếu, không thừa)", () => {
    const enKeys = enLeaves.map(([key]) => key);
    expect(
      viKeys.filter((key) => !enKeys.includes(key)),
      "thiếu ở en",
    ).toEqual([]);
    expect(
      enKeys.filter((key) => !viKeys.includes(key)),
      "thừa ở en",
    ).toEqual([]);
  });

  it("không có chuỗi rỗng và không còn chữ tiếng Việt", () => {
    const vietnamese = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
    for (const [key, value] of enLeaves) {
      expect(value.trim(), `khóa ${key} rỗng`).not.toBe("");
      expect(value, `khóa ${key} còn chữ tiếng Việt`).not.toMatch(vietnamese);
    }
  });
});
