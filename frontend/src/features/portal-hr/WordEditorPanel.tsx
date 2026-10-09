"use client";

import { AlertTriangle, FileCode2, FileText, FileType2, Save, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { portalHrApi } from "@/features/portal-hr/api";
import type { EditorSessionResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./WordEditorPanel.module.scss";

type Translate = (key: string, values?: Record<string, string | number>) => string;

export type SaveFormat = "docx" | "pdf" | "markdown";

type DocEditorHandle = { destroyEditor?: () => void };
type DocsApi = { DocEditor: new (elementId: string, config: Record<string, unknown>) => DocEditorHandle };

function loadEditorScript(src: string): Promise<DocsApi> {
  const existing = (window as unknown as { DocsAPI?: DocsApi }).DocsAPI;
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => {
      const api = (window as unknown as { DocsAPI?: DocsApi }).DocsAPI;
      if (api) resolve(api);
      else reject(new Error("DocsAPI missing"));
    };
    script.onerror = () => reject(new Error("script"));
    document.head.appendChild(script);
  });
}

/** Trình soạn thảo kiểu Word (ONLYOFFICE) nhúng trong trang.
 * "Lưu" hỏi HR muốn lưu **file gốc** dưới dạng PDF hay Markdown rồi mới gửi lệnh lưu; "Hủy" đóng và bỏ mọi thay đổi chưa lưu.
 * Bản Word luôn được giữ làm bản làm việc để mở lại soạn tiếp. */
export function WordEditorPanel({
  documentId,
  versionId,
  onSaved,
  onCancel,
  fill = false,
  barTarget = null,
}: {
  documentId: number;
  versionId: number;
  /** Đã gửi lệnh lưu: cha đợi file về (nếu có thay đổi) rồi đọc lại bản nháp. `format` là định dạng file gốc đã chọn. */
  onSaved: (format: SaveFormat, changed: boolean) => void;
  onCancel: () => void;
  fill?: boolean;
  /** Trang riêng: các nút Lưu/Hủy/Xuất được đặt vào thanh đầu trang (qua portal) để trình soạn thảo sát lên trên. */
  barTarget?: HTMLElement | null;
}) {
  const t = useTranslations("portalDocuments.versions.wordEditor") as unknown as Translate;
  const [session, setSession] = useState<EditorSessionResponseDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [askFormat, setAskFormat] = useState(false);
  const [format, setFormat] = useState<SaveFormat>("docx");
  const [notice, setNotice] = useState<string | null>(null);
  const editorRef = useRef<DocEditorHandle | null>(null);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .openEditorSession(documentId, versionId)
      .then((result) => !cancelled && setSession(result))
      .catch(() => !cancelled && setError("openFailed"));
    return () => {
      cancelled = true;
    };
  }, [documentId, versionId]);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    loadEditorScript(session.api_js_url)
      .then((api) => {
        if (cancelled) return;
        editorRef.current = new api.DocEditor("word-editor-host", session.config);
      })
      .catch(() => !cancelled && setError("scriptFailed"));
    return () => {
      cancelled = true;
      editorRef.current?.destroyEditor?.();
      editorRef.current = null;
    };
  }, [session]);

  async function confirmSave() {
    if (!session) return;
    setSaving(true);
    setNotice(null);
    try {
      const result = await portalHrApi.saveEditorSession(documentId, versionId, session.document_key, format);
      setAskFormat(false);
      if (!result.ok) setNotice("saveFailed");
      else onSaved(format, result.changed);
    } catch {
      setAskFormat(false);
      setNotice("saveFailed");
    } finally {
      setSaving(false);
    }
  }

  const bar = (
    <div className={`${styles.bar} ${barTarget ? styles.barInline : ""}`}>
      {error ? (
        <span className={styles.errorInline} role="alert">
          <AlertTriangle aria-hidden="true" size={14} /> {t(`errors.${error}`)}
        </span>
      ) : null}
      {notice ? (
        <span className={notice === "saveFailed" ? styles.errorInline : styles.noticeInline}>{t(`notice.${notice}`)}</span>
      ) : null}
      <button className={m.btnSec} onClick={onCancel} title={t("cancelHint")} type="button">
        <X aria-hidden="true" size={14} /> {t("cancel")}
      </button>
      <button className={m.btn} disabled={!session || saving} onClick={() => setAskFormat(true)} type="button">
        <Save aria-hidden="true" size={14} /> {t("save")}
      </button>
    </div>
  );

  return (
    <div className={`${styles.wrap} ${fill ? styles.wrapFill : ""}`}>
      {barTarget ? createPortal(bar, barTarget) : bar}
      {fill ? null : <p className={styles.hint}>{t("hint")}</p>}
      <div className={`${styles.host} ${fill ? styles.hostFill : ""}`}>
        <div id="word-editor-host" />
      </div>

      {askFormat ? (
        <PortalModal
          closeLabel={t("saveModal.close")}
          footer={
            <>
              <button className={m.btnSec} disabled={saving} onClick={() => setAskFormat(false)} type="button">
                {t("saveModal.cancel")}
              </button>
              <button className={m.btn} disabled={saving} onClick={confirmSave} type="button">
                <Save aria-hidden="true" size={14} /> {t("saveModal.confirm")}
              </button>
            </>
          }
          icon={Save}
          onClose={() => setAskFormat(false)}
          subtitle={t("saveModal.intro")}
          title={t("saveModal.title")}
          tone="indigo"
        >
          <div className={styles.formats} role="radiogroup">
            {(
              [
                { value: "docx", icon: FileText },
                { value: "pdf", icon: FileType2 },
                { value: "markdown", icon: FileCode2 },
              ] as const
            ).map(({ value, icon: Icon }) => (
              <label className={`${styles.format} ${format === value ? styles.formatOn : ""}`} key={value}>
                <input checked={format === value} name="save-format" onChange={() => setFormat(value)} type="radio" />
                <Icon aria-hidden="true" size={20} />
                <span>
                  <b>{t(`saveModal.${value}.title`)}</b>
                  <small>{t(`saveModal.${value}.hint`)}</small>
                </span>
              </label>
            ))}
          </div>
        </PortalModal>
      ) : null}
    </div>
  );
}
