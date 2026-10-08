import type { TaskGroupDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

export type CreateJourneyTemplateRequestDTO = {
  code: string;
  title: string;
  description?: string | null;
};

export type CreateJourneyStageRequestDTO = {
  title: string;
  sort_order: number;
};

export type CreateAiTaskProposalRequestDTO = {
  document_version_id: number;
};

export type AiTaskSourceChunkRequestDTO = {
  document_section_id: number;
  quote: string;
};

export type AcceptAiTaskProposalRequestDTO = {
  title: string;
  instructions_markdown: string;
  required: boolean;
  source_chunks: AiTaskSourceChunkRequestDTO[];
  // Tách riêng để backend ghép thành ba mục "Vì sao / Điều kiện hoàn thành / Các bước".
  summary?: string | null;
  done_criteria?: string[];
  estimated_minutes?: number | null;
  warnings?: string[];
  task_group?: TaskGroupDTO | null;
  /** Mã các task đã tạo trước đó phải xong trước task này. */
  depends_on?: number[];
  /** Bản nháp của ngày sẽ nhận task; bỏ trống = bản nháp mới nhất (chưa có thì tạo từ bản đang áp dụng). */
  stage_version_id?: number | null;
};

export type CreateAiTaskProposalJobRequestDTO = {
  document_version_ids: number[];
};

export type CopyDocumentVersionRequestDTO = {
  label?: string | null;
};

export type UpdateDocumentVersionRequestDTO = {
  /** Khóa lạc quan: phải bằng `updated_at` lần đọc gần nhất của bản nháp. */
  expected_updated_at: string;
  markdown?: string | null;
  label?: string | null;
  effective_from?: string | null;
  clear_effective_from?: boolean;
};

export type ActivateDocumentVersionRequestDTO = {
  effective_from?: string | null;
};

export type CreateTaskManualRequestDTO = {
  title: string;
  body_markdown: string;
  required: boolean;
  sort_order?: number | null;
  depends_on?: number[];
  task_group?: TaskGroupDTO | null;
};

export type UpdateTaskTemplateRequestDTO = {
  title: string;
  body_markdown: string;
  required: boolean;
  journey_stage_id?: number | null;
  sort_order?: number | null;
  depends_on?: number[] | null;
  task_group?: TaskGroupDTO | null;
};

export type UpdateDocumentRequestDTO = {
  title: string;
  category_slug: string;
};

export type SetDocumentStatusRequestDTO = {
  status: "ACTIVE" | "ARCHIVED";
  /** Chỉ dùng khi tắt: KEEP giữ mọi task, DELETE xóa các task chỉ dựa vào tài liệu này. */
  tasks?: DocumentTaskChoiceDTO;
};

export type CreateAiTaskProposalFromSectionsRequestDTO = {
  document_version_id: number;
  section_ids: number[];
};

export type DocumentTaskChoiceDTO = "KEEP" | "DELETE";

export type CreateStageVersionRequestDTO = {
  /** Sao chép từ bản này; bỏ trống = bản đang áp dụng. */
  from_version_id?: number | null;
  note?: string | null;
  /** Bản nháp rỗng (không sao chép task): thay cả ngày bằng roadmap mới thay vì nối thêm vào task cũ. */
  empty?: boolean;
};
