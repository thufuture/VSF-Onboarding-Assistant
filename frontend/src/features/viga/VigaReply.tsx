"use client";

import { FileText, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { MarkdownText } from "@/components/markdown/MarkdownText";
import { DocumentModal } from "@/features/chat/DocumentModal";
import type {
  VigaAnswerResponseDTO,
  VigaSourceResponseDTO,
} from "@/features/viga/dto/responseDTO/viga.response";
import { ReplyFeedback } from "@/features/viga/ReplyFeedback";
import { useRouter } from "@/i18n/navigation";

import styles from "./VigaReply.module.scss";

const TRANSLATED_KEYS = new Set([
  "notInJourney",
  "allDone",
  "taskDone",
  "taskReady",
  "nextStep",
  "locked",
  "dayPlan",
  "dayPlanEmpty",
  "dayNotFound",
  "progress",
  "taskDetail",
  "clarifyTask",
  "noJourney",
  "noTaskNow",
  "noBasis",
  "outOfScope",
  "assistantUnavailable",
  "smalltalk",
]);

/** Phần hiển thị một câu trả lời của Viga: loại, nội dung (dịch theo khóa nếu có), nguồn trích, việc chặn, hành động gợi ý. */
export function VigaReply({
  reply,
  sentTicketId,
  onReport,
}: {
  reply: VigaAnswerResponseDTO;
  /** Mã ticket đã gửi cho câu này (nếu có): thay nút gửi bằng dòng xác nhận. */
  sentTicketId: number | null;
  onReport: () => void;
}) {
  const t = useTranslations("employee.viga");
  const tt = useTranslations("employee.task");
  const router = useRouter();
  const [source, setSource] = useState<{ source: VigaSourceResponseDTO; quote: string | null } | null>(null);

  // Khóa dịch có trong i18n thì dịch theo ngôn ngữ đang chọn; không có (vd. câu hỏi lại do LLM soạn) thì hiện nguyên văn.
  const message =
    reply.message_key && TRANSLATED_KEYS.has(reply.message_key)
      ? t(`reply.${reply.message_key}`, reply.message_params)
      : reply.message;
  const answers = reply.claims.filter((claim) => claim.response_type === "ANSWER" && claim.text);

  return (
    <div className={styles.reply}>
      <span className={`${styles.type} ${styles[reply.response_type]}`}>{t(`type.${reply.response_type}`)}</span>
      {reply.assumed_task_title ? (
        <p className={styles.assumed}>{t("reply.assumed", { title: reply.assumed_task_title })}</p>
      ) : null}

      {reply.response_type === "ANSWER" && answers.length > 0 ? (
        <div className={styles.claims}>
          {answers.map((claim, index) => (
            <div className={styles.claim} key={index}>
              <MarkdownText className={styles.text}>{claim.text ?? ""}</MarkdownText>
              {claim.quote ? (
                <blockquote>
                  <small>{t("claim.quote")}</small>
                  {claim.quote}
                </blockquote>
              ) : null}
              {claim.source ? (
                <button
                  className={styles.sourceButton}
                  onClick={() => claim.source && setSource({ source: claim.source, quote: claim.quote })}
                  type="button"
                >
                  <FileText aria-hidden="true" size={13} />
                  {claim.source.document_title} · {claim.source.version_label}
                  {claim.source.section_heading ? ` · ${claim.source.section_heading}` : ""}
                </button>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <MarkdownText className={styles.message}>{message}</MarkdownText>
      )}
      {reply.response_type === "ANSWER" && reply.unanswered && reply.unanswered.length > 0 ? (
        <div className={styles.unanswered}>
          <b>{t("claim.unansweredTitle")}</b>
          <ul>
            {reply.unanswered.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <small>{t("claim.unansweredHint")}</small>
        </div>
      ) : reply.response_type === "ANSWER" && reply.claims.some((claim) => claim.response_type === "NO_BASIS") ? (
        <p className={styles.partial}>{t("claim.partialNoBasis")}</p>
      ) : null}

      {reply.blocking_tasks.length > 0 ? (
        <ul className={styles.blocks}>
          {reply.blocking_tasks.map((item) => (
            <li key={item.task_id}>
              <span className={`${styles.dot} ${styles[`dot_${item.state}`]}`} />
              <span>{item.title}</span>
              <small>{tt(`state.${item.state}`)}</small>
            </li>
          ))}
        </ul>
      ) : null}

      {reply.suggested_actions.length > 0 ? (
        <div className={styles.actions}>
          {reply.suggested_actions.map((action, index) => (
            <button
              key={index}
              onClick={() =>
                router.push(
                  action.type === "OPEN_TASK" && action.task_id !== null
                    ? `/me/tasks/${action.task_id}`
                    : { pathname: "/me/tasks", query: { stage: action.stage_id ?? "" } },
                )
              }
              type="button"
            >
              {action.type === "OPEN_TASK"
                ? t("action.openTask", { title: action.title })
                : t("action.openDay", { day: action.title })}
            </button>
          ))}
        </div>
      ) : null}

      {reply.sources.length > 0 ? (
        <p className={styles.sources}>
          {t("sourcesLabel")}{" "}
          {reply.sources
            .map((item) => (item.kind === "TASK" ? t("source.task", { title: item.title }) : t("source.day", { day: item.title })))
            .join(" · ")}
        </p>
      ) : null}

      {reply.can_report_to_hr ? (
        sentTicketId !== null ? (
          <p className={styles.sent}>{t("report.sent", { id: sentTicketId })}</p>
        ) : (
          <button className={styles.report} onClick={onReport} type="button">
            <Send aria-hidden="true" size={13} /> {t("report.button")}
          </button>
        )
      ) : null}

      {reply.message_id > 0 && reply.response_type !== "ERROR" ? (
        <ReplyFeedback initial={reply.feedback} key={reply.message_id} messageId={reply.message_id} />
      ) : null}

      {source ? (
        <DocumentModal
          documentTitle={source.source.document_title}
          documentUrl={source.source.document_url}
          onClose={() => setSource(null)}
          quote={source.quote}
          sectionHeading={source.source.section_heading}
          versionId={source.source.version_id}
          versionLabel={source.source.version_label}
        />
      ) : null}
    </div>
  );
}
