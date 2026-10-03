"use client";

import { BookOpen, FileText } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { DocumentModal } from "@/features/chat/DocumentModal";
import type { TaskSourceDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./TaskSources.module.scss";

/**
 * Nguồn của task: mỗi nguồn là tài liệu, mục và đoạn trích nguyên văn. Bấm "Xem trong tài liệu" mở tài liệu tại đúng mục và
 * tô đúng đoạn trích (không tô cả mục). Task cũ chưa lưu đoạn trích thì chỉ cuộn tới mục.
 */
export function TaskSources({ sources }: { sources: TaskSourceDTO[] }) {
  const t = useTranslations("taskSources");
  const [open, setOpen] = useState<TaskSourceDTO | null>(null);

  if (sources.length === 0) return null;

  return (
    <>
      <ul className={styles.list}>
        {sources.map((source, index) => (
          <li className={styles.item} key={`${source.version_id}-${source.section_heading}-${index}`}>
            <span className={styles.icon}>
              <FileText aria-hidden="true" size={15} />
            </span>
            <div className={styles.text}>
              <b title={source.document_title}>{source.document_title}</b>
              <small>
                {source.version_label}
                {source.section_heading ? ` · ${source.section_heading}` : ""}
              </small>
              {source.quote ? <blockquote>{source.quote}</blockquote> : null}
              <button className={styles.view} onClick={() => setOpen(source)} type="button">
                <BookOpen aria-hidden="true" size={13} /> {t("view")}
              </button>
            </div>
          </li>
        ))}
      </ul>

      {open ? (
        <DocumentModal
          documentTitle={open.document_title}
          documentUrl={open.document_url}
          onClose={() => setOpen(null)}
          quote={open.quote}
          sectionHeading={open.section_heading}
          versionId={open.version_id}
          versionLabel={open.version_label}
        />
      ) : null}
    </>
  );
}
