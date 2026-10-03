"use client";

import { useTranslations } from "next-intl";
import { useCallback, useState, type FormEvent } from "react";

import { vigaApi, VigaError } from "@/features/viga/api";
import type {
  ConversationMessageResponseDTO,
  ConversationResponseDTO,
  VigaAnswerResponseDTO,
  VigaResponseTypeDTO,
} from "@/features/viga/dto/responseDTO/viga.response";

export type Turn = {
  id: string;
  question: string;
  reply: VigaAnswerResponseDTO | null;
  /** Lỗi gọi API (mạng, hỏi quá nhanh, lỗi máy chủ) — khác với các đường thoát hợp lệ của Viga như NO_BASIS. */
  error: string | null;
  ticketId: number | null;
};

/** Dựng lại câu trả lời đã lưu (hội thoại mở lại) từ tin nhắn + payload backend đã ghi lúc trả lời. */
export function replyFromMessage(message: ConversationMessageResponseDTO, conversationId: number): VigaAnswerResponseDTO {
  const payload = message.payload as Partial<VigaAnswerResponseDTO> & {
    actions?: VigaAnswerResponseDTO["suggested_actions"];
    can_report?: boolean;
  };
  return {
    conversation_id: conversationId,
    message_id: message.id,
    new_conversation: false,
    response_type: (message.response_type ?? "INFO") as VigaResponseTypeDTO,
    message: message.content,
    message_key: (payload.message_key as string | null | undefined) ?? null,
    message_params: payload.message_params ?? {},
    claims: payload.claims ?? [],
    blocking_tasks: payload.blocking_tasks ?? [],
    suggested_actions: payload.actions ?? [],
    sources: payload.sources ?? [],
    can_report_to_hr: Boolean(payload.can_report),
    unanswered: (payload.unanswered as string[] | undefined) ?? [],
    assumed_task_title: (payload.assumed_task_title as string | null | undefined) ?? null,
    route: (payload.route as string | undefined) ?? "NONE",
    feedback: message.feedback ?? null,
  };
}

export function turnsFromMessages(messages: ConversationMessageResponseDTO[], conversationId: number): Turn[] {
  const turns: Turn[] = [];
  for (const message of messages) {
    if (message.role === "USER") {
      turns.push({ id: `m${message.id}`, question: message.content, reply: null, error: null, ticketId: null });
    } else if (turns.length > 0) {
      turns[turns.length - 1].reply = replyFromMessage(message, conversationId);
    }
  }
  return turns;
}

/** Việc gắn với ticket: chỉ khi câu trả lời nói về một việc cụ thể (không gắn bừa cho câu hỏi tài liệu). */
export function relatedTaskId(reply: VigaAnswerResponseDTO): number | null {
  if (!["NEXT_STEP", "PREREQUISITE_REQUIRED", "INFO"].includes(reply.response_type)) return null;
  return reply.suggested_actions.find((action) => action.type === "OPEN_TASK")?.task_id ?? null;
}

export type ReportTarget = { turnId: string; question: string; reply: VigaAnswerResponseDTO };

/**
 * Trạng thái và thao tác của một cuộc trò chuyện với Viga, dùng chung cho ngăn bên phải và trang đầy đủ: hỏi, mở lại, đổi tên,
 * xóa, mở cuộc mới, lịch sử và gửi câu hỏi cho HR. Hội thoại lưu trên máy chủ (mục 6.2).
 */
export function useVigaChat() {
  const t = useTranslations("employee.viga");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<ConversationResponseDTO[] | null>(null);
  const [renaming, setRenaming] = useState<{ id: number; title: string } | null>(null);
  const [report, setReport] = useState<ReportTarget | null>(null);

  const errorText = useCallback(
    (error: unknown): string => {
      if (error instanceof VigaError && error.code === "throttled") {
        return t("errors.throttled", { seconds: error.retryAfter ?? 30 });
      }
      if (error instanceof VigaError && error.code === "network") return t("errors.network");
      return t("errors.unavailable");
    },
    [t],
  );

  const send = useCallback(
    async (asked: string): Promise<void> => {
      const trimmed = asked.trim();
      if (!trimmed || busy) return;
      const id = `q${Date.now()}`;
      setTurns((current) => [...current, { id, question: trimmed, reply: null, error: null, ticketId: null }]);
      setDraft("");
      setBusy(true);
      try {
        const result = await vigaApi.ask({ question: trimmed, conversation_id: conversationId });
        setConversationId(result.conversation_id);
        setHistory(null); // danh sách cuộc trò chuyện đổi (cuộc mới / cập nhật): nạp lại khi mở
        setTurns((current) => current.map((turn) => (turn.id === id ? { ...turn, reply: result } : turn)));
      } catch (caught) {
        setTurns((current) => current.map((turn) => (turn.id === id ? { ...turn, error: errorText(caught) } : turn)));
      } finally {
        setBusy(false);
      }
    },
    [busy, conversationId, errorText],
  );

  const loadHistory = useCallback(async (): Promise<void> => {
    try {
      setHistory(await vigaApi.listConversations());
    } catch {
      setHistory([]);
    }
  }, []);

  const openConversation = useCallback(
    async (id: number): Promise<boolean> => {
      try {
        const detail = await vigaApi.getConversation(id);
        setConversationId(id);
        setTurns(turnsFromMessages(detail.messages, id));
        return true;
      } catch (caught) {
        setTurns((current) => [
          ...current,
          { id: `e${Date.now()}`, question: "", reply: null, error: errorText(caught), ticketId: null },
        ]);
        return false;
      }
    },
    [errorText],
  );

  const newConversation = useCallback(() => {
    setConversationId(null);
    setTurns([]);
  }, []);

  const removeConversation = useCallback(
    async (id: number): Promise<void> => {
      try {
        await vigaApi.deleteConversation(id);
        setHistory((current) => (current ? current.filter((item) => item.id !== id) : current));
        if (id === conversationId) {
          // Xóa đúng cuộc đang mở: trả về màn chào nhưng giữ danh sách lịch sử để xóa/mở tiếp.
          setConversationId(null);
          setTurns([]);
        }
      } catch {
        /* giữ nguyên danh sách: xóa không thành thì người dùng thử lại */
      }
    },
    [conversationId],
  );

  const saveRename = useCallback(
    async (event: FormEvent): Promise<void> => {
      event.preventDefault();
      if (!renaming || !renaming.title.trim()) return;
      try {
        const updated = await vigaApi.renameConversation(renaming.id, renaming.title.trim());
        setHistory((current) => (current ? current.map((item) => (item.id === updated.id ? updated : item)) : current));
        setRenaming(null);
      } catch {
        /* giữ ô nhập để thử lại */
      }
    },
    [renaming],
  );

  const markTicketSent = useCallback((turnId: string, ticketId: number) => {
    setTurns((current) => current.map((turn) => (turn.id === turnId ? { ...turn, ticketId } : turn)));
  }, []);

  return {
    turns,
    conversationId,
    draft,
    setDraft,
    busy,
    history,
    renaming,
    setRenaming,
    report,
    setReport,
    send,
    loadHistory,
    openConversation,
    newConversation,
    removeConversation,
    saveRename,
    markTicketSent,
  };
}
