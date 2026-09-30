import { describe, expect, it } from "vitest";

import type { EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { buildDays } from "./journeyModel";
import { askViga, type VigaText } from "./vigaMock";

const TEXT: VigaText = {
  notInJourney: "chưa có căn cứ",
  allDone: "đã xong rồi",
  nextStep: (title) => `bước kế tiếp ${title}`,
  locked: (title, blocker) => `${title} cần ${blocker}`,
  dayPlan: (day, ready, total) => `${day}: ${ready}/${total}`,
  dayPlanEmpty: (day) => `${day}: không có việc`,
  openTask: (title) => `mở ${title}`,
  openDay: (day) => `xem ${day}`,
  sourceTask: (title) => `nguồn ${title}`,
  sourceDay: (day) => `nguồn ${day}`,
};

function task(overrides: Partial<EmployeeTaskResponseDTO> & { id: number; title: string }): EmployeeTaskResponseDTO {
  return {
    task_template_id: overrides.id,
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

const LAPTOP = task({ id: 1, title: "Nhận laptop và đăng nhập Outlook" });
const SIGNATURE = task({
  id: 2,
  title: "Ảnh đại diện và chữ ký email",
  status: "LOCKED",
  prerequisites: [{ title: "Nhận laptop và đăng nhập Outlook", done: false }],
});
const TASKS = [LAPTOP, SIGNATURE];
const DAYS = buildDays(TASKS);

describe("askViga", () => {
  it("không khớp việc nào thì nói thẳng chưa có căn cứ, không đoán", () => {
    const reply = askViga("Lương tháng này bao giờ có?", TASKS, DAYS, TEXT);

    expect(reply.responseType).toBe("NOT_IN_JOURNEY");
    expect(reply.actions).toEqual([]);
    expect(reply.sources).toEqual([]);
  });

  it("hỏi về việc đang mở thì chỉ ra bước kế tiếp kèm nút mở việc", () => {
    const reply = askViga("Mình nhận laptop thế nào?", TASKS, DAYS, TEXT);

    expect(reply.responseType).toBe("NEXT_STEP");
    expect(reply.message).toContain("Nhận laptop");
    expect(reply.actions[0]).toMatchObject({ type: "OPEN_TASK", taskId: LAPTOP.id });
  });

  it("hỏi về việc đang khóa thì nêu đúng việc phải làm trước", () => {
    const reply = askViga("Chữ ký email làm sao?", TASKS, DAYS, TEXT);

    expect(reply.responseType).toBe("PREREQUISITE_REQUIRED");
    expect(reply.message).toContain("Nhận laptop và đăng nhập Outlook");
    expect(reply.blockingTasks).toEqual([{ taskId: LAPTOP.id, title: LAPTOP.title, state: "ready" }]);
    expect(reply.actions[0]).toMatchObject({ type: "OPEN_TASK", taskId: LAPTOP.id });
  });

  it("hỏi hôm nay làm gì thì trả kế hoạch ngày đang dở", () => {
    const reply = askViga("Hôm nay mình cần làm gì?", TASKS, DAYS, TEXT);

    expect(reply.responseType).toBe("DAY_PLAN");
    expect(reply.message).toBe("Ngày 1: 1/2");
    expect(reply.actions[0]).toMatchObject({ type: "OPEN_DAY", stageId: 1 });
  });

  it("việc đã xong thì trả lời là đã hoàn thành", () => {
    const done = [{ ...LAPTOP, status: "DONE" as const }];
    const reply = askViga("Nhận laptop", done, buildDays(done), TEXT);

    expect(reply.responseType).toBe("INFO");
    expect(reply.message).toBe(TEXT.allDone);
  });

  it("lộ trình rỗng thì không gợi ý bừa", () => {
    expect(askViga("Hôm nay làm gì?", [], [], TEXT).responseType).toBe("NOT_IN_JOURNEY");
  });
});
