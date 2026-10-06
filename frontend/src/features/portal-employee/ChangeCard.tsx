"use client";

import { Check, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import type {
  ChangeContentDTO,
  ChangePreviewResponseDTO,
  TaskChangeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";
import { Link } from "@/i18n/navigation";

import styles from "./ChangeCard.module.scss";
import { fieldValue, isPending, plainBody, visibleFields, type ChangeField } from "./changeModel";
import shared from "./employee.module.scss";

type Props = {
  change: TaskChangeResponseDTO;
  busy: boolean;
  previewChange: (changeId: number) => Promise<ChangePreviewResponseDTO>;
  onAccept: (changeId: number) => void;
  onDismiss: (changeId: number) => void;
  /** Dùng trong trang chi tiết việc: gọn hơn và không có đường dẫn tới chính việc đó. */
  compact?: boolean;
};

/**
 * Một việc HR vừa chỉnh: khung trước/sau, hộp ghi chú nói rõ nút "Cập nhật" sẽ làm gì (lấy từ máy chủ, KHÔNG ghi gì khi xem),
 * và hai nút "Cập nhật" / "Giữ bản cũ". Việc đã làm xong vẫn giữ trạng thái Đã xong sau khi cập nhật.
 */
export function ChangeCard({ change, busy, previewChange, onAccept, onDismiss, compact = false }: Props) {
  const t = useTranslations("employee.changes");
  const tt = useTranslations("employee.task");
  const pending = isPending(change);
  const [preview, setPreview] = useState<ChangePreviewResponseDTO | null>(null);

  useEffect(() => {
    if (!pending) return;
    let cancelled = false;
    previewChange(change.id)
      .then((result) => {
        if (!cancelled) setPreview(result);
      })
      .catch(() => {
        /* không có ghi chú chi tiết thì vẫn hiện ghi chú chung */
      });
    return () => {
      cancelled = true;
    };
  }, [change.id, pending, previewChange]);

  function render(field: ChangeField, content: ChangeContentDTO | null): string | null {
    const value = fieldValue(content, field);
    if (value === undefined) return null;
    if (field === "required") return value ? tt("required") : tt("optional");
    if (field === "task_group") return tt(`group.${(value as string | null) ?? "NONE"}`);
    if (field === "prerequisites") {
      const list = value as string[];
      return list.length > 0 ? list.join(", ") : t("noPrerequisites");
    }
    return field === "body_markdown" ? plainBody(String(value)) : String(value);
  }

  const fields = visibleFields(change);
  const showBefore = change.kind !== "ADDED";
  const showAfter = change.kind !== "REMOVED";
  const doneNow = change.employee_status === "DONE";

  return (
    <article className={`${styles.card} ${compact ? styles.compact : ""}`} data-testid="change-card">
      <header className={styles.head}>
        <span className={styles.kind}>{t(`kind.${change.kind}`)}</span>
        <h3>{change.task_title}</h3>
        {doneNow ? <span className={styles.doneTag}>{t("alreadyDone")}</span> : null}
        <span className={styles.stage}>{change.stage_title}</span>
      </header>

      {change.informational ? (
        <p className={styles.resolved}>{t("keptDone")}</p>
      ) : (
        <div className={styles.diff}>
          {fields.map((field) => {
            const before = render(field, change.before);
            const after = render(field, change.after);
            const long = field === "body_markdown";
            return (
              <div className={styles.field} key={field}>
                <b>{t(`field.${field}`)}</b>
                <div className={`${styles.sides} ${showBefore && showAfter ? "" : styles.single}`}>
                  {showBefore ? (
                    <div className={`${styles.side} ${styles.before} ${long ? styles.long : ""}`}>
                      <small>{t("before")}</small>
                      {before ?? <span className={styles.empty}>{t("empty")}</span>}
                    </div>
                  ) : null}
                  {showAfter ? (
                    <div className={`${styles.side} ${styles.after} ${long ? styles.long : ""}`}>
                      <small>{t("after")}</small>
                      {after ?? <span className={styles.empty}>{t("empty")}</span>}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {pending ? (
        <div className={styles.note}>
          <b>{t("noteTitle")}</b>
          <ul>
            <li>{t("noteKeepStatus")}</li>
            {preview?.keeps_done ? <li>{t("noteKeepsDone")}</li> : null}
            {preview?.removes_task ? <li>{t("noteRemoves")}</li> : null}
            {preview && preview.also_update.length > 0 ? (
              <li>{t("noteAlsoUpdate", { titles: preview.also_update.join(", ") })}</li>
            ) : null}
            {preview && preview.locked_until.length > 0 ? (
              <li>{t("noteLockedUntil", { titles: preview.locked_until.join(", ") })}</li>
            ) : null}
            <li>{t("noteKeepOld")}</li>
          </ul>
        </div>
      ) : (
        <p className={styles.resolved}>{t(`status.${change.status}`)}</p>
      )}

      <div className={styles.actions}>
        {pending ? (
          <>
            <button className={shared.btn} disabled={busy} onClick={() => onAccept(change.id)} type="button">
              {busy ? <Loader2 aria-hidden="true" size={14} /> : <Check aria-hidden="true" size={14} />} {t("accept")}
            </button>
            <button className={shared.btnGhost} disabled={busy} onClick={() => onDismiss(change.id)} type="button">
              {t("keepOld")}
            </button>
          </>
        ) : null}
        {!compact && change.employee_task_id !== null && change.kind !== "REMOVED" ? (
          <Link className={shared.btnGhost} href={`/me/tasks/${change.employee_task_id}`}>
            {t("openTask")}
          </Link>
        ) : null}
      </div>
    </article>
  );
}
