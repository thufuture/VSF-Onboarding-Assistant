import type { ChatAskRequestDTO } from "@/features/chat/dto/requestDTO/chat.request";
import type { ChatAskResponseDTO } from "@/features/chat/dto/responseDTO/chat.response";
import type { DocumentContentResponseDTO } from "@/features/chat/dto/responseDTO/document.response";
import type { ErrorResponseDTO } from "@/types/apiError";

export type ChatErrorCode = "unauthorized" | "unavailable" | "network";

export class ChatError extends Error {
  readonly code: ChatErrorCode;

  constructor(code: ChatErrorCode) {
    super(code);
    this.name = "ChatError";
    this.code = code;
  }
}

async function readErrorCode(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as Partial<ErrorResponseDTO>;
    return typeof body.code === "string" ? body.code : null;
  } catch {
    return null;
  }
}

/** Hỏi `POST /api/v1/chat/ask`. Câu hỏi có thể bị backend tách thành nhiều claim (mục 6, kế hoạch 2-C/2-D). */
async function ask(question: string): Promise<ChatAskResponseDTO> {
  const body: ChatAskRequestDTO = { question };
  let response: Response;
  try {
    response = await fetch("/api/v1/chat/ask", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ChatError("network");
  }

  if (response.status === 401) throw new ChatError("unauthorized");
  if (!response.ok) {
    void (await readErrorCode(response));
    throw new ChatError("unavailable");
  }

  try {
    return (await response.json()) as ChatAskResponseDTO;
  } catch {
    throw new ChatError("unavailable");
  }
}

/** Toàn bộ nội dung tài liệu (Markdown), dùng cho modal xem nguồn — thay vì bắt tải file gốc rồi tự tìm. */
async function getDocument(versionId: number): Promise<DocumentContentResponseDTO> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/chat/documents/${versionId}`, { credentials: "include" });
  } catch {
    throw new ChatError("network");
  }

  if (response.status === 401) throw new ChatError("unauthorized");
  if (!response.ok) {
    void (await readErrorCode(response));
    throw new ChatError("unavailable");
  }

  try {
    return (await response.json()) as DocumentContentResponseDTO;
  } catch {
    throw new ChatError("unavailable");
  }
}

export const chatApi = { ask, getDocument };
