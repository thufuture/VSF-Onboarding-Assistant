import type { RoadState } from "@/components/roadmap/JourneyRoad";
import type { EmployeeTaskResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

export type Day = {
  stageId: number;
  title: string;
  order: number;
  tasks: EmployeeTaskResponseDTO[];
  done: number;
  total: number;
  pct: number;
};

export function stateOf(task: EmployeeTaskResponseDTO): RoadState {
  if (task.status === "DONE" || task.status === "SKIPPED") return "done";
  if (task.status === "LOCKED") return "locked";
  return "ready";
}

/** Gom task theo ngày (giai đoạn), ngày và task đều theo thứ tự HR đã sắp. */
export function buildDays(tasks: EmployeeTaskResponseDTO[]): Day[] {
  const byStage = new Map<number, Day>();
  for (const task of tasks) {
    let day = byStage.get(task.stage_id);
    if (!day) {
      day = { stageId: task.stage_id, title: task.stage_title, order: task.stage_sort_order, tasks: [], done: 0, total: 0, pct: 0 };
      byStage.set(task.stage_id, day);
    }
    day.tasks.push(task);
  }
  const days = [...byStage.values()].sort((a, b) => a.order - b.order || a.stageId - b.stageId);
  for (const day of days) {
    day.tasks.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
    day.total = day.tasks.length;
    day.done = day.tasks.filter((task) => stateOf(task) === "done").length;
    day.pct = day.total ? Math.round((day.done / day.total) * 100) : 0;
  }
  return days;
}

export type Progress = {
  done: number;
  total: number;
  pct: number;
  ready: number;
  locked: number;
  requiredDone: number;
  requiredTotal: number;
};

export function progressOf(tasks: EmployeeTaskResponseDTO[]): Progress {
  const done = tasks.filter((task) => stateOf(task) === "done").length;
  const requiredTasks = tasks.filter((task) => task.required);
  return {
    done,
    total: tasks.length,
    pct: tasks.length ? Math.round((done / tasks.length) * 100) : 0,
    ready: tasks.filter((task) => stateOf(task) === "ready").length,
    locked: tasks.filter((task) => stateOf(task) === "locked").length,
    requiredDone: requiredTasks.filter((task) => stateOf(task) === "done").length,
    requiredTotal: requiredTasks.length,
  };
}

/** Tên gọi trong tiếng Việt: từ cuối của "Họ Đệm Tên". */
export function givenName(displayName: string): string {
  const words = displayName.trim().split(/\s+/).filter(Boolean);
  return words[words.length - 1] ?? displayName;
}
