// Máy trả lời của Viga ở bản dựng giao diện: CHƯA gọi API (`POST /chat/ask` có thật nhưng trang này chưa nối).
// Câu trả lời được suy ra từ lộ trình THẬT của người đang đăng nhập (tên task, trạng thái, tiên quyết) theo đúng
// hình dạng dữ liệu của prototype v15: response_type + message + blocking_tasks + suggested_actions + sources.
// Khi nối API thật, thay `askViga` bằng lời gọi mạng và giữ nguyên kiểu `VigaReply`.

import type { EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { stateOf, type Day } from "./journeyModel";

export type VigaResponseType = "NEXT_STEP" | "PREREQUISITE_REQUIRED" | "DAY_PLAN" | "INFO" | "NOT_IN_JOURNEY";

export type VigaAction =
  | { type: "OPEN_TASK"; taskId: number; label: string }
  | { type: "OPEN_DAY"; stageId: number; label: string };

export type VigaReply = {
  responseType: VigaResponseType;
  message: string;
  blockingTasks: { taskId: number; title: string; state: "done" | "ready" | "locked" }[];
  actions: VigaAction[];
  sources: string[];
};

export type VigaText = {
  notInJourney: string;
  allDone: string;
  nextStep: (title: string) => string;
  locked: (title: string, blocker: string) => string;
  dayPlan: (day: string, ready: number, total: number) => string;
  dayPlanEmpty: (day: string) => string;
  openTask: (title: string) => string;
  openDay: (day: string) => string;
  sourceTask: (title: string) => string;
  sourceDay: (day: string) => string;
};

/** Ý định hỏi: khớp từ khóa tiếng Việt rồi tìm task tương ứng trong lộ trình thật bằng chính tiêu đề task. */
const DAY_ASK = /hôm nay|ngày mai|ngày \d|hôm sau|làm gì|việc nào|bắt đầu từ đâu|kế hoạch/i;

function matchTask(question: string, tasks: EmployeeTaskResponseDTO[]): EmployeeTaskResponseDTO | null {
  const words = question
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .filter((word) => word.length >= 3);
  if (words.length === 0) return null;

  let best: { task: EmployeeTaskResponseDTO; score: number } | null = null;
  for (const task of tasks) {
    const haystack = `${task.title} ${task.body_markdown}`.toLowerCase();
    const score = words.filter((word) => haystack.includes(word)).length;
    if (score > 0 && (!best || score > best.score)) best = { task, score };
  }
  // Cần khớp ít nhất 2 từ (hoặc toàn bộ từ khi câu rất ngắn) để không trả lời bừa.
  return best && best.score >= Math.min(2, words.length) ? best.task : null;
}

function currentDay(days: Day[]): Day | null {
  return days.find((day) => day.done < day.total) ?? days[days.length - 1] ?? null;
}

/** Trả lời một câu hỏi dựa trên lộ trình thật; không khớp được thì nói thẳng "chưa có trong lộ trình". */
export function askViga(question: string, tasks: EmployeeTaskResponseDTO[], days: Day[], text: VigaText): VigaReply {
  if (DAY_ASK.test(question)) {
    const day = currentDay(days);
    if (day) {
      const ready = day.tasks.filter((task) => stateOf(task) === "ready");
      const first = ready[0];
      return {
        responseType: "DAY_PLAN",
        message: ready.length
          ? text.dayPlan(day.title, ready.length, day.total)
          : text.dayPlanEmpty(day.title),
        blockingTasks: day.tasks.slice(0, 6).map((task) => ({ taskId: task.id, title: task.title, state: stateOf(task) })),
        actions: [
          { type: "OPEN_DAY", stageId: day.stageId, label: text.openDay(day.title) },
          ...(first ? [{ type: "OPEN_TASK" as const, taskId: first.id, label: text.openTask(first.title) }] : []),
        ],
        sources: [text.sourceDay(day.title)],
      };
    }
  }

  const task = matchTask(question, tasks);
  if (!task) {
    return { responseType: "NOT_IN_JOURNEY", message: text.notInJourney, blockingTasks: [], actions: [], sources: [] };
  }

  const state = stateOf(task);
  if (state === "done") {
    return {
      responseType: "INFO",
      message: text.allDone,
      blockingTasks: [],
      actions: [{ type: "OPEN_TASK", taskId: task.id, label: text.openTask(task.title) }],
      sources: [text.sourceTask(task.title)],
    };
  }

  if (state === "locked") {
    const blockers = task.prerequisites.filter((item) => !item.done);
    const blockerTasks = tasks.filter((row) => blockers.some((item) => item.title === row.title));
    return {
      responseType: "PREREQUISITE_REQUIRED",
      message: text.locked(task.title, blockers[0]?.title ?? ""),
      blockingTasks: blockerTasks.map((row) => ({ taskId: row.id, title: row.title, state: stateOf(row) })),
      actions: blockerTasks.length
        ? [{ type: "OPEN_TASK", taskId: blockerTasks[0].id, label: text.openTask(blockerTasks[0].title) }]
        : [{ type: "OPEN_TASK", taskId: task.id, label: text.openTask(task.title) }],
      sources: [text.sourceTask(task.title)],
    };
  }

  return {
    responseType: "NEXT_STEP",
    message: text.nextStep(task.title),
    blockingTasks: [],
    actions: [{ type: "OPEN_TASK", taskId: task.id, label: text.openTask(task.title) }],
    sources: [text.sourceTask(task.title)],
  };
}
