import { describe, expect, it } from "vitest";

import { fieldValue, isAutoApplied, isPending, plainBody, summarizeNotice, visibleFields } from "./changeModel";
import type { TaskChangeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

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

  it("việc thêm và bỏ đã áp dụng là tự động; việc sửa hoặc còn chờ thì không", () => {
    expect(isAutoApplied({ kind: "ADDED", status: "ACCEPTED" })).toBe(true);
    expect(isAutoApplied({ kind: "REMOVED", status: "ACCEPTED" })).toBe(true);
    expect(isAutoApplied({ kind: "MODIFIED", status: "ACCEPTED" })).toBe(false);
    expect(isAutoApplied({ kind: "ADDED", status: "PENDING" })).toBe(false); // thông báo cũ chưa xử lý vẫn cần chấp nhận
  });

  it("gói một thông báo thành việc thêm, bỏ, giữ lại vì đã xong và việc cần xem", () => {
    const row = (kind: TaskChangeResponseDTO["kind"], status: TaskChangeResponseDTO["status"], title: string, informational = false) =>
      ({ kind, status, task_title: title, informational }) as TaskChangeResponseDTO;
    const summary = summarizeNotice([
      row("ADDED", "ACCEPTED", "A"),
      row("REMOVED", "ACCEPTED", "B"),
      row("REMOVED", "DISMISSED", "C", true),
      row("MODIFIED", "PENDING", "D"),
      row("MODIFIED", "ACCEPTED", "E"),
    ]);
    expect(summary).toEqual({ added: ["A"], removed: ["B"], keptDone: ["C"], review: ["D"] });
  });
});
