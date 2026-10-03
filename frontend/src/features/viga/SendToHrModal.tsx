"use client";

import { Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { vigaApi, VigaError } from "@/features/viga/api";
import type { TicketSummaryResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

const KNOWN = new Set(["TICKET_DAILY_LIMIT", "TICKET_DUPLICATE", "NO_TEAM_ASSIGNED"]);

/**
 * Hộp xác nhận "Gửi câu hỏi này cho HR" (mục 17.5): nhân viên XEM và SỬA câu hỏi, thêm ghi chú rồi mới gửi.
 * Viga không bao giờ tự tạo ticket; ticket chỉ được tạo sau khi bấm "Gửi" ở đây.
 */
export function SendToHrModal({
  question,
  conversationId,
  employeeTaskId,
  onClose,
  onSent,
}: {
  question: string;
  conversationId: number | null;
  employeeTaskId: number | null;
  onClose: () => void;
  onSent: (ticket: TicketSummaryResponseDTO) => void;
}) {
  const t = useTranslations("employee.viga.report");
  const [text, setText] = useState(question);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const ticket = await vigaApi.createTicket({
        question: text.trim(),
        note: note.trim() || null,
        employee_task_id: employeeTaskId,
        conversation_id: conversationId,
      });
      onSent(ticket);
    } catch (caught) {
      const apiCode = caught instanceof VigaError ? caught.apiCode : null;
      setError(apiCode && KNOWN.has(apiCode) ? t(`errors.${apiCode}`) : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PortalModal
      closeLabel={t("close")}
      footer={
        <>
          <button className={m.btnSec} onClick={onClose} type="button">
            {t("cancel")}
          </button>
          <button className={m.btn} disabled={busy || !text.trim()} form="send-to-hr" type="submit">
            <Send aria-hidden="true" size={14} /> {t("send")}
          </button>
        </>
      }
      icon={Send}
      onClose={onClose}
      subtitle={t("subtitle")}
      title={t("title")}
      tone="indigo"
    >
      <form id="send-to-hr" onSubmit={submit}>
        <p className={m.faint}>{t("intro")}</p>
        {error ? (
          <p className={m.faint} role="alert" style={{ color: "#a3121f" }}>
            {error}
          </p>
        ) : null}
        <div className={m.fgrid} style={{ marginTop: 12 }}>
          <div className={m.span2}>
            <label htmlFor="hr-question">{t("question")}</label>
            <textarea
              id="hr-question"
              maxLength={2000}
              onChange={(event) => setText(event.target.value)}
              required
              rows={4}
              value={text}
            />
          </div>
          <div className={m.span2}>
            <label htmlFor="hr-note">{t("note")}</label>
            <textarea
              id="hr-note"
              maxLength={1000}
              onChange={(event) => setNote(event.target.value)}
              placeholder={t("notePlaceholder")}
              rows={3}
              value={note}
            />
          </div>
        </div>
        <p className={m.faint}>{t("limits")}</p>
      </form>
    </PortalModal>
  );
}
