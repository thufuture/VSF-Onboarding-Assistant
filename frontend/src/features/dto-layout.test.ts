import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Quy ước DTO của VSF (giống Ralion): mỗi feature có `dto/requestDTO/<tên>.request.ts` và
 * `dto/responseDTO/<tên>.response.ts`; kiểu tên `XxxRequestDTO` / `XxxResponseDTO`. Kiểu lỗi dùng chung nằm ở `src/types`.
 */
const FEATURES = join(__dirname);

function dtoDirs(): string[] {
  return readdirSync(FEATURES)
    .map((name) => join(FEATURES, name, "dto"))
    .filter((path) => existsSync(path) && statSync(path).isDirectory());
}

function exportedTypes(file: string): string[] {
  return [...readFileSync(file, "utf8").matchAll(/^export type (\w+)/gm)].map((match) => match[1]);
}

describe("bố cục dto của các feature", () => {
  it("có ít nhất feature auth với requestDTO và responseDTO", () => {
    const auth = join(FEATURES, "auth", "dto");
    expect(existsSync(join(auth, "requestDTO", "auth.request.ts"))).toBe(true);
    expect(existsSync(join(auth, "responseDTO", "auth.response.ts"))).toBe(true);
  });

  it("thư mục dto chỉ chứa requestDTO và responseDTO", () => {
    for (const dir of dtoDirs()) {
      for (const entry of readdirSync(dir)) {
        expect(["requestDTO", "responseDTO"], `${dir}/${entry}`).toContain(entry);
      }
    }
  });

  it("tên tệp và tên kiểu theo đúng quy ước", () => {
    for (const dir of dtoDirs()) {
      for (const [folder, kind, suffix] of [
        ["requestDTO", "request", "RequestDTO"],
        ["responseDTO", "response", "ResponseDTO"],
      ] as const) {
        const sub = join(dir, folder);
        if (!existsSync(sub)) continue;
        for (const file of readdirSync(sub)) {
          expect(file, `${sub}/${file}`).toMatch(new RegExp(`\\.${kind}\\.ts$`));
          const names = exportedTypes(join(sub, file));
          // Kiểu phụ (ví dụ UserRoleDTO) cũng phải kết thúc bằng DTO; mỗi tệp phải có kiểu chính đúng hậu tố.
          for (const name of names) expect(name, `${sub}/${file}: ${name}`).toMatch(/DTO$/);
          expect(
            names.some((name) => name.endsWith(suffix)),
            `${sub}/${file} cần một kiểu ${suffix}`,
          ).toBe(true);
        }
      }
    }
  });

  it("kiểu lỗi dùng chung ở src/types và khớp hợp đồng backend", () => {
    const file = join(__dirname, "..", "types", "apiError.ts");
    expect(exportedTypes(file)).toEqual(["ErrorResponseDTO"]);
    const source = readFileSync(file, "utf8");
    for (const field of ["code", "message_key", "detail"]) expect(source).toContain(field);
  });
});
