"use client";

import { AlertTriangle, Archive, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { portalHrApi } from "@/features/portal-hr/api";
import type { DocumentTaskChoiceDTO } from "@/features/portal-hr/dto/requestDTO/portal.request";
import type {
  DocumentImpactResponseDTO,
  DocumentListItemResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./DocumentRemovalModal.module.scss";

const LISTED_TASKS = 5;

/** Tắt (archive) hoặc xóa tài liệu. Nếu đã có task trích dẫn tài liệu, hỏi giữ hay xóa các task đó trước khi làm. */
export function DocumentRemovalModal({
  mode,
  doc,
  busy,
  onCancel,
  onConfirm,
}: {
  mode: "archive" | "delete";
  doc: DocumentListItemResponseDTO;
  busy: boolean;
  onCancel: () => void;
  onConfirm: (tasks: DocumentTaskChoiceDTO | undefined) => void;
}) {
  const t = useTranslations("portalDocuments.removal");
  const common = useTranslations("portalDocuments");
  const [impact, setImpact] = useState<DocumentImpactResponseDTO | null>(null);
  const [failed, setFailed] = useState(false);
  const [choice, setChoice] = useState<DocumentTaskChoiceDTO>("KEEP");

  useEffect(() => {
    let alive = true;
    portalHrApi
      .getDocumentImpact(doc.id)
      .then((result) => alive && setImpact(result))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [doc.id]);

  const isDelete = mode === "delete";
  const Icon = isDelete ? Trash2 : Archive;
  const onlyTasks = impact?.only_tasks ?? [];
  const sharedTasks = impact?.shared_tasks ?? [];
  const hasTasks = onlyTasks.length + sharedTasks.length > 0;
  const blocked = isDelete && impact?.processing === true;
  const ready = impact !== null && !failed;

  return (
    <PortalModal
      closeLabel={common("close")}
      footer={
        <>
          <button className={m.btnSec} onClick={onCancel} type="button">
            {common("cancel")}
          </button>
          <button
            className={m.btnDanger}
            disabled={busy || !ready || blocked}
            onClick={() => onConfirm(hasTasks ? choice : undefined)}
            type="button"
          >
            <Icon aria-hidden="true" size={14} /> {isDelete ? t("deleteButton") : common("archiveConfirmButton")}
          </button>
        </>
      }
      icon={Icon}
      onClose={onCancel}
      subtitle={doc.title}
      title={isDelete ? t("deleteTitle") : common("archiveConfirmTitle", { title: doc.title })}
      tone="rose"
      wide
    >
      <p className={styles.lead}>{isDelete ? t("deleteBody", { count: impact?.version_count ?? doc.version_count }) : common("archiveConfirmBody")}</p>

      {failed ? <p className={styles.error}>{t("loadFailed")}</p> : null}
      {impact === null && !failed ? <p className={styles.muted}>{t("loading")}</p> : null}
      {blocked ? (
        <div className={m.noteWarn}>
          <AlertTriangle aria-hidden="true" size={14} />
          <span>{t("processing")}</span>
        </div>
      ) : null}

      {ready && hasTasks ? (
        <>
          <div className={m.noteWarn}>
            <AlertTriangle aria-hidden="true" size={14} />
            <span>{t(isDelete ? "warnDelete" : "warnArchive", { count: onlyTasks.length + sharedTasks.length })}</span>
          </div>

          <ul className={styles.tasks}>
            {[...onlyTasks, ...sharedTasks].slice(0, LISTED_TASKS).map((task) => (
              <li key={task.id}>
                <b>{task.title}</b>
                <small>
                  {task.day_title}
                  {sharedTasks.some((s) => s.id === task.id) ? ` · ${t("sharedTag")}` : ""}
                </small>
              </li>
            ))}
            {onlyTasks.length + sharedTasks.length > LISTED_TASKS ? (
              <li className={styles.more}>{t("more", { count: onlyTasks.length + sharedTasks.length - LISTED_TASKS })}</li>
            ) : null}
          </ul>

          <fieldset className={styles.choices}>
            <legend>{t("choose")}</legend>
            <label className={choice === "KEEP" ? styles.on : ""}>
              <input checked={choice === "KEEP"} name="task-choice" onChange={() => setChoice("KEEP")} type="radio" />
              <span>
                <b>{t("keep")}</b>
                <small>{t(isDelete ? "keepHintDelete" : "keepHintArchive")}</small>
              </span>
            </label>
            <label className={`${choice === "DELETE" ? styles.on : ""} ${onlyTasks.length === 0 ? styles.disabled : ""}`}>
              <input
                checked={choice === "DELETE"}
                disabled={onlyTasks.length === 0}
                name="task-choice"
                onChange={() => setChoice("DELETE")}
                type="radio"
              />
              <span>
                <b>{t("removeTasks", { count: onlyTasks.length })}</b>
                <small>{onlyTasks.length === 0 ? t("removeNone") : t("removeHint", { shared: sharedTasks.length })}</small>
              </span>
            </label>
          </fieldset>

          {impact.employee_copies > 0 ? (
            <p className={styles.muted}>{t("employeeCopies", { count: impact.employee_copies })}</p>
          ) : null}
        </>
      ) : null}
    </PortalModal>
  );
}
