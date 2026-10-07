import type { ChangeContentDTO, TaskChangeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

/** Các trường có thể đổi của một việc, theo thứ tự hiển thị. `sort_order` không bao giờ được coi là thay đổi. */
export const FIELD_ORDER = ["title", "body_markdown", "required", "task_group", "prerequisites"] as const;
export type ChangeField = (typeof FIELD_ORDER)[number];

/** Trường cần hiện ở khung trước/sau: việc sửa chỉ hiện trường đã đổi; việc mới hoặc bị bỏ hiện nội dung chính của việc đó. */
export function visibleFields(change: Pick<TaskChangeResponseDTO, "kind" | "changed_fields">): ChangeField[] {
  if (change.kind === "ADDED" || change.kind === "REMOVED") return ["title", "body_markdown", "required", "task_group", "prerequisites"];
  return FIELD_ORDER.filter((field) => change.changed_fields.includes(field));
}

/** Giá trị của một trường trong nội dung lưu ở thông báo; `undefined` nghĩa là bản đó không có nội dung (việc mới không có "trước"). */
export function fieldValue(content: ChangeContentDTO | null, field: ChangeField): ChangeContentDTO[ChangeField] | undefined {
  if (!content) return undefined;
  return content[field];
}

/** Nội dung hướng dẫn dạng chữ thường để so sánh trước/sau: bỏ dấu `#` đầu dòng của tiêu đề markdown. */
export function plainBody(markdown: string): string {
  return markdown.replace(/^#{1,6}\s*/gm, "").trim();
}

/** Thay đổi còn chờ nhân viên quyết định (bỏ dòng chỉ báo thông tin của việc đã làm bị bỏ). */
export function isPending(change: Pick<TaskChangeResponseDTO, "status" | "informational">): boolean {
  return change.status === "PENDING" && !change.informational;
}

/** Việc thêm hoặc bỏ đã được áp dụng TỰ ĐỘNG khi HR cập nhật (nhân viên không phải bấm gì). */
export function isAutoApplied(change: Pick<TaskChangeResponseDTO, "kind" | "status">): boolean {
  return (change.kind === "ADDED" || change.kind === "REMOVED") && change.status === "ACCEPTED";
}

export type NoticeSummaryData = {
  added: string[];
  removed: string[];
  /** Việc HR đã bỏ nhưng bạn đã làm xong nên vẫn được giữ. */
  keptDone: string[];
  /** Việc cần bạn xem và quyết định (sửa nội dung, đổi tiên quyết; cả thông báo cũ chưa xử lý). */
  review: string[];
};

/** Gói các thay đổi của một thông báo thành các nhóm để hiện "đã đổi gì" trong một khung. */
export function summarizeNotice(changes: TaskChangeResponseDTO[]): NoticeSummaryData {
  const titles = (pick: (change: TaskChangeResponseDTO) => boolean) =>
    changes.filter(pick).map((change) => change.task_title);
  return {
    added: titles((c) => c.kind === "ADDED" && isAutoApplied(c)),
    removed: titles((c) => c.kind === "REMOVED" && isAutoApplied(c)),
    keptDone: titles((c) => c.informational),
    review: titles((c) => isPending(c)),
  };
}
