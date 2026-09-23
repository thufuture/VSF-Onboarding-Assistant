/** Phản hồi của `GET /api/v1/chat/documents/{version_id}` (khớp `DocumentContentResponseDTO`). */
export type DocumentContentResponseDTO = {
  document_title: string;
  version_label: string;
  markdown: string;
};
