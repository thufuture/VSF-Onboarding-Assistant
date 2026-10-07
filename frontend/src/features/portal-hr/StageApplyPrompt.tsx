"use client";

import { CheckCircle2, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type { StageDraftChangeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { Link } from "@/i18n/navigation";

import styles from "./DocumentRemovalModal.module.scss";

/**
 * Sau khi xóa/tắt tài liệu kèm xóa task: việc xóa mới chỉ nằm ở BẢN NHÁP của từng ngày. Hỏi HR có cập nhật cho nhân viên luôn
 * không; cập nhật thì mỗi nhân viên nhận đúng MỘT thông báo cho mỗi ngày (việc xóa tự rời lộ trình), để sau thì xử lý ở Quản lý task.
 */
export function StageApplyPrompt({
  changes,
  onClose,
  onDone,
}: {
  changes: StageDraftChangeResponseDTO[];
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const t = useTranslations("portalDocuments.removal");
  const common = useTranslations("portalDocuments");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function applyAll() {
    setBusy(true);
    setError(null);
    let done = 0;
    for (const change of changes) {
      try {
        await portalHrApi.applyStageVersion(change.version_id);
        done += 1;
      } catch (caught) {
        const empty = caught instanceof PortalError && caught.apiCode === "VERSION_EMPTY";
        setError(empty ? t("applyEmpty", { day: change.stage_title }) : common("errors.unavailable"));
        setBusy(false);
        return;
      }
    }
    setBusy(false);
    onDone(t("applyDone", { days: done }));
  }

  return (
    <PortalModal
      closeLabel={common("close")}
      footer={
        <>
          <button className={m.btnSec} onClick={onClose} type="button">
            {t("applyLater")}
          </button>
          <button className={m.btn} disabled={busy} onClick={() => void applyAll()} type="button">
            <Send aria-hidden="true" size={14} /> {t("applyNow")}
          </button>
        </>
      }
      icon={CheckCircle2}
      onClose={onClose}
      title={t("applyTitle")}
      tone="teal"
      wide
    >
      <p className={styles.lead}>{t("applyBody", { count: changes.length })}</p>
      <ul className={styles.tasks}>
        {changes.map((change) => (
          <li key={change.stage_id}>
            <b>{t("applyDay", { day: change.stage_title, count: change.removed_tasks, n: change.version_no })}</b>
            <small>
              <Link href={`/admin/tasks?stage=${change.stage_id}`}>{t("applyOpenTasks")}</Link>
            </small>
          </li>
        ))}
      </ul>
      {error ? <p className={styles.error}>{error}</p> : null}
    </PortalModal>
  );
}
