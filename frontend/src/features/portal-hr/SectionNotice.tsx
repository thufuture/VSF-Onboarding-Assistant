"use client";

import { Eye, FileText, Sparkles, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { DocumentModal } from "@/features/chat/DocumentModal";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type { AiTaskProposalResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./SectionNotice.module.scss";

type SectionRef = { section_id: number; heading: string | null };

/**
 * Cảnh báo "AI coi N mục là chỉ có thông tin" (hoặc "N mục chưa có task"): mỗi mục có Xem (mở tài liệu, cuộn tới đúng mục như
 * khi xem nguồn của một task), Tạo task (AI soạn task cho đúng mục đó, chèn vào roadmap đúng vị trí theo thứ tự tài liệu) và
 * Loại bỏ (HR xem rồi, mục chỉ là thông tin, bỏ khỏi cảnh báo).
 */
export function SectionNotice({
  kind,
  versionId,
  documentTitle,
  versionLabel,
  sections,
  disabled,
  onAdd,
}: {
  kind: "skippedInfo" | "uncovered";
  versionId: number;
  documentTitle: string;
  versionLabel: string;
  sections: SectionRef[];
  disabled: boolean;
  /** Chèn đề xuất vào roadmap; trả về true nếu đã thêm (để ẩn mục khỏi cảnh báo). */
  onAdd: (sectionId: number, proposals: AiTaskProposalResponseDTO[]) => Promise<boolean>;
}) {
  const t = useTranslations("portalHr.result");
  const [done, setDone] = useState<Set<number>>(new Set());
  const [working, setWorking] = useState<number | null>(null);
  const [viewing, setViewing] = useState<SectionRef | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const remaining = sections.filter((s) => !done.has(s.section_id));
  const hide = (sectionId: number) => setDone((current) => new Set(current).add(sectionId));

  async function create(section: SectionRef): Promise<boolean> {
    setMessage(null);
    setWorking(section.section_id);
    try {
      const proposals = await portalHrApi.proposeAiTasksFromSections({
        document_version_id: versionId,
        section_ids: [section.section_id],
      });
      if (await onAdd(section.section_id, proposals)) hide(section.section_id);
      return true;
    } catch (caught) {
      const code = caught instanceof PortalError ? caught.apiCode : null;
      setMessage(code === "NO_TASK_FROM_SECTION" ? t("section.noTask") : t("section.failed"));
      return false;
    } finally {
      setWorking(null);
    }
  }

  if (remaining.length === 0) return null;
  return (
    <div className={styles.notice}>
      <p>{t(kind === "skippedInfo" ? "skippedInfoLead" : "uncoveredLead", { count: remaining.length })}</p>
      <ul>
        {remaining.map((section) => (
          <li key={section.section_id}>
            <FileText aria-hidden="true" size={13} />
            <span title={section.heading ?? ""}>{section.heading || t("section.untitled")}</span>
            <button className={styles.ghost} disabled={working !== null} onClick={() => setViewing(section)} type="button">
              <Eye aria-hidden="true" size={13} /> {t("section.view")}
            </button>
            <button
              className={styles.primary}
              disabled={disabled || working !== null}
              onClick={() => void create(section)}
              type="button"
            >
              <Sparkles aria-hidden="true" size={13} />{" "}
              {working === section.section_id ? t("section.creating") : t("section.create")}
            </button>
            <button
              className={styles.ghost}
              disabled={working !== null}
              onClick={() => hide(section.section_id)}
              type="button"
            >
              <X aria-hidden="true" size={13} /> {t("section.dismiss")}
            </button>
          </li>
        ))}
      </ul>
      {message ? <p className={styles.error}>{message}</p> : null}

      {viewing ? (
        <DocumentModal
          actions={
            <>
              <button
                className={styles.ghost}
                disabled={working !== null}
                onClick={() => {
                  hide(viewing.section_id);
                  setViewing(null);
                }}
                type="button"
              >
                <X aria-hidden="true" size={13} /> {t("section.dismiss")}
              </button>
              <button
                className={styles.primary}
                data-primary
                disabled={disabled || working !== null}
                onClick={async () => {
                  if (await create(viewing)) setViewing(null);
                }}
                type="button"
              >
                <Sparkles aria-hidden="true" size={13} />{" "}
                {working === viewing.section_id ? t("section.creating") : t("section.createFromThis")}
              </button>
            </>
          }
          documentTitle={documentTitle}
          documentUrl=""
          onClose={() => setViewing(null)}
          quote={viewing.heading}
          sectionHeading={viewing.heading}
          versionId={versionId}
          versionLabel={versionLabel}
        />
      ) : null}
    </div>
  );
}
