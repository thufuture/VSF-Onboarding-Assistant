import type { FlatIconName, FlatTone } from "@/components/flat-icons/FlatIcon";
import type { TaskGroupDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

export type TaskGroupStyle = { key: TaskGroupDTO | null; color: string; flat: FlatIconName; tone: FlatTone };

// Nhóm task cố định (Hồ sơ / Đào tạo / Thiết bị / Văn phòng): mỗi nhóm một màu dịu và một icon phẳng; chưa phân nhóm dùng xám.
export const TASK_GROUPS: (TaskGroupStyle & { key: TaskGroupDTO })[] = [
  { key: "PROFILE", color: "#1f8a5f", flat: "file", tone: "green" },
  { key: "TRAINING", color: "#1b6fb8", flat: "book", tone: "blue" },
  { key: "DEVICE", color: "#4457b3", flat: "laptop", tone: "indigo" },
  { key: "OFFICE", color: "#d18a12", flat: "building", tone: "amber" },
];

export const NO_GROUP: TaskGroupStyle = { key: null, color: "#6b7a8c", flat: "tasks", tone: "slate" };

export function groupStyle(group: TaskGroupDTO | null): TaskGroupStyle {
  return TASK_GROUPS.find((g) => g.key === group) ?? NO_GROUP;
}
