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
};
