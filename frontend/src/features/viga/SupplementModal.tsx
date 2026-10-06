"use client";

import { CheckCircle2, FilePlus2, RefreshCw, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { JobProgress } from "@/components/job-progress/JobProgress";
import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import type { JobResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { useJob } from "@/features/portal-hr/useJob";

import { vigaApi } from "./api";
import type { RecheckGapResponseDTO } from "./dto/responseDTO/viga.response";
import styles from "./SupplementModal.module.scss";

type Stage = "form" | "working" | "checking" | "result" | "failed";

/**
 * "Bổ sung tài liệu" ngay trên câu hỏi Viga chưa trả lời được: HR sửa câu hỏi cho rõ, viết đáp án đúng và đầu mối; hệ thống thêm
 * vào tài liệu "Hỏi đáp bổ sung" của phòng ban, kích hoạt (chạy nền, có phần trăm) rồi tự hỏi lại Viga để biết đã trả lời được chưa.
 * Chỉ khi trả lời được thì câu mới tự đánh dấu đã xử lý.
 */
export function SupplementModal({
  gapId,
  source = "gap",
  question,
  onClose,
  onResolved,
}: {
  /** Mã câu chưa trả lời được (`source="gap"`) hoặc mã nhóm 👎 (`source="feedback"`). */
  gapId: number;
  source?: "gap" | "feedback";
  question: string;
  onClose: () => void;
  onResolved: () => void;
}) {
  const t = useTranslations("viga.feedback.supplement");
  const [asked, setAsked] = useState(question);
  const [answer, setAnswer] = useState("");
  const [contact, setContact] = useState("");
  const [stage, setStage] = useState<Stage>("form");
  const [jobId, setJobId] = useState<number | null>(null);
  const [result, setResult] = useState<RecheckGapResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function check() {
    setStage("checking");
    try {
      const outcome = await (source === "feedback" ? vigaApi.recheckDissatisfied(gapId) : vigaApi.recheckContentGap(gapId));
      setResult(outcome);
      setStage("result");
      if (outcome.answered) onResolved();
    } catch {
      setError(t("errors.recheck"));
      setStage("failed");
    }
  }

  const { job } = useJob(jobId, (finished: JobResponseDTO) => {
    if (finished.status === "SUCCEEDED") {
      void check();
    } else {
      setError(t("errors.activation"));
      setStage("failed");
    }
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (answer.trim().length < 5) return;
    setError(null);
    setStage("working");
    try {
      const body = { answer: answer.trim(), question: asked.trim() || null, contact: contact.trim() || null };
      const created = await (source === "feedback"
        ? vigaApi.supplementDissatisfied(gapId, body)
        : vigaApi.supplementContentGap(gapId, body));
      setJobId(created.job_id);
    } catch {
      setError(t("errors.save"));
      setStage("failed");
    }
  }

  const busy = stage === "working" || stage === "checking";
  const answered = stage === "result" && result?.answered === true;

  return (
    <PortalModal
      closeLabel={t("close")}
      footer={
        stage === "form" ? (
          <>
            <button className={m.btnSec} onClick={onClose} type="button">
              {t("cancel")}
            </button>
            <button className={m.btn} disabled={answer.trim().length < 5} form="supplement-form" type="submit">
              <FilePlus2 aria-hidden="true" size={14} /> {t("submit")}
            </button>
          </>
        ) : stage === "result" || stage === "failed" ? (
          <>
            {!answered ? (
              <button className={m.btnSec} onClick={() => setStage("form")} type="button">
                <RefreshCw aria-hidden="true" size={14} /> {t("edit")}
              </button>
            ) : null}
            <button className={m.btn} onClick={onClose} type="button">
              {t("close")}
            </button>
          </>
        ) : undefined
      }
      icon={FilePlus2}
      onClose={busy ? () => undefined : onClose}
      subtitle={t("subtitle")}
      title={t("title")}
      tone="amber"
      wide
    >
      {stage === "form" || stage === "failed" ? (
        <form className={styles.form} id="supplement-form" onSubmit={submit}>
          <p className={styles.hint}>{t("hint")}</p>
          <div className={styles.field}>
            <label htmlFor="sup-question">{t("question")}</label>
            <input id="sup-question" maxLength={300} onChange={(event) => setAsked(event.target.value)} type="text" value={asked} />
          </div>
          <div className={styles.field}>
            <label htmlFor="sup-answer">{t("answer")}</label>
            <textarea
              id="sup-answer"
              maxLength={3000}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder={t("answerPlaceholder")}
              required
              rows={6}
              value={answer}
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="sup-contact">{t("contact")}</label>
            <input
              id="sup-contact"
              maxLength={200}
              onChange={(event) => setContact(event.target.value)}
              placeholder={t("contactPlaceholder")}
              type="text"
              value={contact}
            />
          </div>
          {error ? (
            <p className={styles.error} role="alert">
              <TriangleAlert aria-hidden="true" size={14} /> {error}
            </p>
          ) : null}
        </form>
      ) : null}

      {stage === "working" ? (
        <div className={styles.working}>
          <p>{t("working")}</p>
          <JobProgress
            percent={job?.progress_percent ?? 0}
            stage={job?.stage ?? t("starting")}
            state={job?.status === "RUNNING" ? "running" : "pending"}
          />
        </div>
      ) : null}

      {stage === "checking" ? (
        <div className={styles.working}>
          <p>{t("checking")}</p>
          <JobProgress percent={100} stage={t("checkingStage")} state="running" />
        </div>
      ) : null}

      {stage === "result" && result ? (
        result.answered ? (
          <div className={styles.ok}>
            <b>
              <CheckCircle2 aria-hidden="true" size={16} /> {t("okTitle")}
            </b>
            <p>{result.message}</p>
            {result.document_title ? (
              <small>
                {result.document_title}
                {result.section_heading ? ` · ${result.section_heading}` : ""}
              </small>
            ) : null}
            <small>{t("closed")}</small>
          </div>
        ) : (
          <div className={styles.miss}>
            <b>
              <TriangleAlert aria-hidden="true" size={16} /> {t("missTitle")}
            </b>
            <p>{t("missBody")}</p>
          </div>
        )
      ) : null}
    </PortalModal>
  );
}
