"use client";

import { Eye, FileText, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  AiTaskProposalResponseDTO,
  DocumentSectionResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./SectionNotice.module.scss";

type SectionRef = { section_id: number; heading: string | null };

/**
 * Cảnh báo "AI coi N mục là chỉ có thông tin" (hoặc "N mục chưa có task"): mỗi mục có nút Xem (đọc nội dung gốc) và
 * "Tạo task" (AI soạn task cho đúng mục đó rồi thêm thẳng vào roadmap đang duyệt, HR không phải nhập tay).
 */
export function SectionNotice({
  kind,
  versionId,
  sections,
  disabled,
  onAdd,
}: {
  kind: "skippedInfo" | "uncovered";
  versionId: number;
  sections: SectionRef[];
  disabled: boolean;
  /** Đưa đề xuất vào roadmap; trả về true nếu đã thêm (để ẩn mục khỏi cảnh báo). */
  onAdd: (proposals: AiTaskProposalResponseDTO[]) => boolean;
}) {
  const t = useTranslations("portalHr.result");
  const [done, setDone] = useState<Set<number>>(new Set());
  const [working, setWorking] = useState<number | null>(null);
  const [viewing, setViewing] = useState<SectionRef | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const remaining = sections.filter((s) => !done.has(s.section_id));

  async function create(section: SectionRef): Promise<boolean> {
    setMessage(null);
    setWorking(section.section_id);
    try {
      const proposals = await portalHrApi.proposeAiTasksFromSections({
        document_version_id: versionId,
        section_ids: [section.section_id],
      });
      if (onAdd(proposals)) setDone((current) => new Set(current).add(section.section_id));
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
            <button
              className={styles.ghost}
              disabled={working !== null}
              onClick={() => setViewing(section)}
              type="button"
            >
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
          </li>
        ))}
      </ul>
      {message ? <p className={styles.error}>{message}</p> : null}

      {viewing ? (
        <SectionViewer
          busy={working !== null}
          disabled={disabled}
          onClose={() => setViewing(null)}
          onCreate={async () => {
            if (await create(viewing)) setViewing(null);
          }}
          section={viewing}
          versionId={versionId}
        />
      ) : null}
    </div>
  );
}

function SectionViewer({
  versionId,
  section,
  busy,
  disabled,
  onClose,
  onCreate,
}: {
  versionId: number;
  section: SectionRef;
  busy: boolean;
  disabled: boolean;
  onClose: () => void;
  onCreate: () => void;
}) {
  const t = useTranslations("portalHr.result");
  const [data, setData] = useState<DocumentSectionResponseDTO | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    portalHrApi
      .getDocumentSection(versionId, section.section_id)
      .then((result) => alive && setData(result))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [versionId, section.section_id]);

  return (
    <PortalModal
      closeLabel={t("section.close")}
      footer={
        <>
          <button className={m.btnSec} onClick={onClose} type="button">
            {t("section.close")}
          </button>
          <button className={m.btn} disabled={busy || disabled || data === null} onClick={onCreate} type="button">
            <Sparkles aria-hidden="true" size={14} /> {busy ? t("section.creating") : t("section.createFromThis")}
          </button>
        </>
      }
      icon={FileText}
      onClose={onClose}
      subtitle={data ? `${data.document_title} · ${data.version_label}` : undefined}
      title={section.heading || t("section.untitled")}
      tone="indigo"
      wide
    >
      {failed ? <p className={styles.error}>{t("section.loadFailed")}</p> : null}
      {data === null && !failed ? <p className={styles.muted}>{t("section.loading")}</p> : null}
      {data ? <pre className={styles.content}>{data.content}</pre> : null}
      <p className={styles.muted}>{t("section.viewHint")}</p>
    </PortalModal>
  );
}
