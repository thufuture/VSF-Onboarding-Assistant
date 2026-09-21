import { describe, expect, it } from "vitest";

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
      "landing.hero.title",
      "landing.hero.description",
      "landing.hero.primary",
      "landing.hero.demoBadge",
      "landing.steps.title",
      "landing.features.title",
      "landing.footer.demo",
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
