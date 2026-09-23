"use client";

import { ExternalLink, FileText, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { chatApi, ChatError } from "@/features/chat/api";

import styles from "./DocumentModal.module.scss";

type DocumentSection = { level: number; heading: string | null; body: string };

// Cùng quy tắc tách section với backend (chunker.py): H1-H3 mở section mới, mọi văn bản trước heading đầu
// tiên thuộc section "không tiêu đề".
const HEADING_LINE = /^(#{1,3})\s+(.*)$/;

function splitIntoSections(markdown: string): DocumentSection[] {
  const sections: DocumentSection[] = [];
  let current: DocumentSection = { level: 0, heading: null, body: "" };
  for (const line of markdown.split("\n")) {
    const match = HEADING_LINE.exec(line);
    if (match) {
      if (current.heading !== null || current.body.trim()) sections.push(current);
      current = { level: match[1].length, heading: match[2].trim(), body: "" };
    } else {
      current.body += (current.body ? "\n" : "") + line;
    }
  }
  if (current.heading !== null || current.body.trim()) sections.push(current);
  return sections;
}

export type DocumentModalProps = {
  versionId: number;
  documentTitle: string;
  versionLabel: string;
  documentUrl: string;
  sectionHeading: string | null;
  onClose: () => void;
};

/** Modal xem nội dung tài liệu đã nạp, tự cuộn tới đúng section đã trích dẫn — đỡ người dùng phải tự tìm. */
export function DocumentModal({
  versionId,
  documentTitle,
  versionLabel,
  documentUrl,
  sectionHeading,
  onClose,
}: DocumentModalProps) {
  const t = useTranslations("chat.documentModal");
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const highlightRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let cancelled = false;
    chatApi
      .getDocument(versionId)
      .then((response) => {
        if (!cancelled) setMarkdown(response.markdown);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setErrorCode(caught instanceof ChatError ? caught.code : "network");
      });
    return () => {
      cancelled = true;
    };
  }, [versionId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Cuộn tới đúng section ngay khi nội dung đã hiện, không phải bắt người dùng tự tìm.
  // jsdom (test) không cài scrollIntoView — bỏ qua an toàn thay vì lỗi cả hàm.
  useEffect(() => {
    highlightRef.current?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }, [markdown]);

  const sections = useMemo(() => (markdown === null ? [] : splitIntoSections(markdown)), [markdown]);
  const normalizedTarget = sectionHeading?.trim().toLowerCase() ?? null;
  let matched = false;

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <div
        aria-labelledby="document-modal-title"
        aria-modal="true"
        className={styles.modal}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <header className={styles.header}>
          <span aria-hidden="true" className={styles.headerIcon}>
            <FileText size={16} />
          </span>
          <div className={styles.headerText}>
            <b id="document-modal-title">{documentTitle}</b>
            <span>{versionLabel}</span>
          </div>
          <button aria-label={t("close")} className={styles.closeButton} onClick={onClose} type="button">
            <X size={18} />
          </button>
        </header>

        <div className={styles.body}>
          {errorCode ? (
            <p className={styles.status}>{t("loadFailed")}</p>
          ) : markdown === null ? (
            <p className={styles.status}>{t("loading")}</p>
          ) : (
            sections.map((section, index) => {
              const isMatch =
                !matched && normalizedTarget !== null && section.heading?.trim().toLowerCase() === normalizedTarget;
              if (isMatch) matched = true;
              return (
                <section
                  className={isMatch ? styles.sectionHighlighted : styles.section}
                  key={index}
                  ref={isMatch ? highlightRef : undefined}
                >
                  {section.heading ? <h3>{section.heading}</h3> : null}
                  <div className={styles.markdown}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.body.trim()}</ReactMarkdown>
                  </div>
                </section>
              );
            })
          )}
        </div>

        <footer className={styles.footer}>
          {documentUrl.startsWith("http") ? (
            <a href={documentUrl} rel="noopener noreferrer" target="_blank">
              <ExternalLink aria-hidden="true" size={14} />
              {t("openOriginal")}
            </a>
          ) : (
            <span />
          )}
          <button onClick={onClose} type="button">
            {t("close")}
          </button>
        </footer>
      </div>
    </div>
  );
}
