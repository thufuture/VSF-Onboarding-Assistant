import { describe, expect, it } from "vitest";

import type { EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { buildDays, givenName, progressOf, stateOf } from "./journeyModel";

function task(overrides: Partial<EmployeeTaskResponseDTO> & { id: number }): EmployeeTaskResponseDTO {
  return {
    task_template_id: overrides.id,
    title: `Việc ${overrides.id}`,
    body_markdown: "",
    required: true,
    stage_id: 1,
    stage_title: "Ngày 1",
    stage_sort_order: 1,
    sort_order: overrides.id,
    task_group: null,
    status: "READY",
    completed_at: null,
    prerequisites: [],
    ...overrides,
  };
}

describe("stateOf", () => {
  it("gộp 7 trạng thái của backend về 3 trạng thái hiển thị", () => {
    expect(stateOf(task({ id: 1, status: "DONE" }))).toBe("done");
    expect(stateOf(task({ id: 2, status: "SKIPPED" }))).toBe("done");
    expect(stateOf(task({ id: 3, status: "LOCKED" }))).toBe("locked");
    expect(stateOf(task({ id: 4, status: "READY" }))).toBe("ready");
    expect(stateOf(task({ id: 5, status: "IN_PROGRESS" }))).toBe("ready");
    expect(stateOf(task({ id: 6, status: "WAITING_EXTERNAL" }))).toBe("ready");
  });
});

describe("buildDays", () => {
  const tasks = [
    task({ id: 3, stage_id: 2, stage_title: "Ngày 2", stage_sort_order: 2, sort_order: 1 }),
    task({ id: 2, sort_order: 2, status: "LOCKED" }),
    task({ id: 1, sort_order: 1, status: "DONE" }),
  ];

  it("gom theo ngày, giữ thứ tự HR đã sắp và tính tiến độ từng ngày", () => {
    const days = buildDays(tasks);

    expect(days.map((day) => day.title)).toEqual(["Ngày 1", "Ngày 2"]);
    expect(days[0].tasks.map((row) => row.id)).toEqual([1, 2]);
    expect(days[0].done).toBe(1);
    expect(days[0].total).toBe(2);
    expect(days[0].pct).toBe(50);
    expect(days[1].pct).toBe(0);
  });

  it("lộ trình rỗng thì không có ngày nào", () => {
    expect(buildDays([])).toEqual([]);
  });
});

describe("progressOf", () => {
  it("đếm riêng việc bắt buộc và làm tròn phần trăm", () => {
    const progress = progressOf([
      task({ id: 1, status: "DONE" }),
      task({ id: 2, status: "READY" }),
      task({ id: 3, status: "LOCKED", required: false }),
    ]);

    expect(progress).toMatchObject({ done: 1, total: 3, pct: 33, ready: 1, locked: 1, requiredDone: 1, requiredTotal: 2 });
  });

  it("chưa có việc nào thì phần trăm là 0, không chia cho 0", () => {
    expect(progressOf([]).pct).toBe(0);
  });
});

describe("givenName", () => {
  it("lấy tên gọi (từ cuối) trong tên tiếng Việt", () => {
    expect(givenName("Nguyễn Văn An")).toBe("An");
    expect(givenName("  Trần   Thị Bích Hồng ")).toBe("Hồng");
    expect(givenName("An")).toBe("An");
  });
});
