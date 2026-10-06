"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { vigaApi } from "@/features/viga/api";
import type { VigaFeedbackReasonDTO, VigaFeedbackSummaryDTO } from "@/features/viga/dto/responseDTO/viga.response";

import styles from "./ReplyFeedback.module.scss";

const REASONS: VigaFeedbackReasonDTO[] = ["WRONG", "MISSING", "UNCLEAR", "OFF_TOPIC"];

/**
 * 👍/👎 dưới mỗi câu trả lời của Viga (mỗi câu một đánh giá, bấm lại để gỡ). 👎 mở hàng chọn nhanh lý do và ô ghi chú, cả hai đều
 * không bắt buộc. HR chỉ thấy đánh giá ẩn danh theo phòng ban.
 */
export function ReplyFeedback({
  messageId,
  initial,
}: {
  messageId: number;
  initial: VigaFeedbackSummaryDTO | null | undefined;
}) {
  const t = useTranslations("employee.viga.feedback");
  const [rating, setRating] = useState<"UP" | "DOWN" | null>(initial?.rating ?? null);
  const [reason, setReason] = useState<string | null>(initial?.reason ?? null);
  const [comment, setComment] = useState("");
  // Đã gửi ghi chú: gập phần chọn lý do và ô ghi chú lại, chỉ còn lời cảm ơn (có nút sửa lại).
  const [folded, setFolded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save(next: "UP" | "DOWN", nextReason: string | null, nextComment: string | null) {
    setBusy(true);
    setFailed(false);
    try {
      await vigaApi.rateAnswer(messageId, {
        rating: next,
        reason: next === "DOWN" ? (nextReason as VigaFeedbackReasonDTO | null) : null,
        comment: next === "DOWN" ? nextComment : null,
      });
      setRating(next);
      setReason(next === "DOWN" ? nextReason : null);
      return true;
    } catch {
      setFailed(true);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function toggle(next: "UP" | "DOWN") {
    if (busy) return;
    if (rating === next) {
      setBusy(true);
      try {
        await vigaApi.clearRating(messageId);
        setRating(null);
        setReason(null);
        setFolded(false);
      } catch {
        setFailed(true);
      } finally {
        setBusy(false);
      }
      return;
    }
    setFolded(false);
    await save(next, null, null);
  }

  async function chooseReason(next: VigaFeedbackReasonDTO) {
    if (busy) return;
    const value = reason === next ? null : next;
    await save("DOWN", value, comment.trim() || null);
  }

  async function submitComment(event: FormEvent) {
    event.preventDefault();
    if (busy || !comment.trim()) return;
    if (await save("DOWN", reason, comment.trim())) {
      setFolded(true);
    }
  }

  return (
    <div className={styles.feedback}>
      <div className={styles.row} role="group" aria-label={t("question")}>
        <span className={styles.ask}>{t("question")}</span>
        <button
          aria-label={t("up")}
          aria-pressed={rating === "UP"}
          className={`${styles.btn} ${rating === "UP" ? styles.up : ""}`}
          disabled={busy}
          onClick={() => void toggle("UP")}
          title={t("up")}
          type="button"
        >
          <ThumbsUp aria-hidden="true" size={13} />
        </button>
        <button
          aria-label={t("down")}
          aria-pressed={rating === "DOWN"}
          className={`${styles.btn} ${rating === "DOWN" ? styles.down : ""}`}
          disabled={busy}
          onClick={() => void toggle("DOWN")}
          title={t("down")}
          type="button"
        >
          <ThumbsDown aria-hidden="true" size={13} />
        </button>
        {rating === "UP" ? <small className={styles.thanks}>{t("thanks")}</small> : null}
        {failed ? (
          <small className={styles.error} role="alert">
            {t("failed")}
          </small>
        ) : null}
      </div>

      {rating === "DOWN" && folded ? (
        <div className={styles.folded}>
          <small className={styles.thanks}>{t("thanks")}</small>
          <button className={styles.editAgain} onClick={() => setFolded(false)} type="button">
            {t("editAgain")}
          </button>
        </div>
      ) : null}

      {rating === "DOWN" && !folded ? (
        <div className={styles.more}>
          <small>{t("reasonLabel")}</small>
          <div className={styles.chips}>
            {REASONS.map((item) => (
              <button
                aria-pressed={reason === item}
                className={`${styles.chip} ${reason === item ? styles.chipOn : ""}`}
                disabled={busy}
                key={item}
                onClick={() => void chooseReason(item)}
                type="button"
              >
                {t(`reasons.${item}`)}
              </button>
            ))}
          </div>
          <form className={styles.comment} onSubmit={submitComment}>
            <input
              aria-label={t("commentPlaceholder")}
              maxLength={500}
              onChange={(event) => setComment(event.target.value)}
              placeholder={t("commentPlaceholder")}
              value={comment}
            />
            <button disabled={busy || !comment.trim()} type="submit">
              {t("send")}
            </button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
