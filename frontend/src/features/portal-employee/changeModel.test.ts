import { describe, expect, it } from "vitest";

import { fieldValue, isPending, plainBody, visibleFields } from "./changeModel";

describe("changeModel", () => {
  it("việc sửa chỉ hiện các trường đã đổi, theo thứ tự cố định", () => {
    expect(visibleFields({ kind: "MODIFIED", changed_fields: ["prerequisites", "title"] })).toEqual(["title", "prerequisites"]);
  });

  it("việc mới hoặc bị bỏ hiện đủ các trường chính", () => {
    expect(visibleFields({ kind: "ADDED", changed_fields: [] })).toHaveLength(5);
    expect(visibleFields({ kind: "REMOVED", changed_fields: [] })).toHaveLength(5);
  });

  it("sort_order không bao giờ hiện", () => {
    expect(visibleFields({ kind: "MODIFIED", changed_fields: ["sort_order"] })).toEqual([]);
  });

  it("giá trị trường lấy từ nội dung, thiếu nội dung thì undefined", () => {
    expect(fieldValue({ title: "A" }, "title")).toBe("A");
    expect(fieldValue(null, "title")).toBeUndefined();
  });

  it("nội dung hướng dẫn bỏ dấu # của tiêu đề markdown nhưng giữ các bước", () => {
    expect(plainBody("## Vì sao\nĐể làm A.\n\n## Các bước\n1. Làm A")).toBe("Vì sao\nĐể làm A.\n\nCác bước\n1. Làm A");
  });

  it("chỉ báo thông tin hoặc đã xử lý thì không còn chờ quyết định", () => {
    expect(isPending({ status: "PENDING", informational: false })).toBe(true);
    expect(isPending({ status: "PENDING", informational: true })).toBe(false);
    expect(isPending({ status: "ACCEPTED", informational: false })).toBe(false);
  });
});
