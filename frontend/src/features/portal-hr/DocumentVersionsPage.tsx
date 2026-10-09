"use client";

import { CheckCircle2, UploadCloud } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { portalHrApi } from "@/features/portal-hr/api";
import type { DocumentListItemResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { useRouter } from "@/i18n/navigation";

import { DocumentVersionsModal } from "./DocumentVersionsModal";
import styles from "./DocumentsListPage.module.scss";

type Load = { state: "loading" } | { state: "missing" } | { state: "error" } | { state: "ready"; doc: DocumentListItemResponseDTO };

/** Trang riêng của một tài liệu (/admin/documents/[id]): phiên bản, xem, so sánh, soạn thảo kiểu Word, kích hoạt. Thay cho cửa sổ nổi. */
export function DocumentVersionsPage({ documentId }: { documentId: number }) {
  const t = useTranslations("portalDocuments");
  const router = useRouter();
  const [toastNode, showToast] = useToast();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  // Đổi giá trị này để dựng lại phần phiên bản (đọc lại danh sách) sau khi tải thêm phiên bản mới.
  const [reloadKey, setReloadKey] = useState(0);

  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const [activate, setActivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const reloadDoc = useCallback(() => {
    portalHrApi
      .listDocuments()
      .then((items) => {
        const found = items.find((item) => item.id === documentId);
        setLoad(found ? { state: "ready", doc: found } : { state: "missing" });
      })
      .catch(() => setLoad({ state: "error" }));
  }, [documentId]);

  useEffect(() => {
    reloadDoc();
  }, [reloadDoc]);

  async function submitUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setUploadError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("version_label", label);
      form.append("document_id", String(documentId));
      if (effectiveFrom) form.append("effective_from", effectiveFrom);
      if (activate) form.append("activate", "true");
      const result = await portalHrApi.uploadDocument(form);
      setUploading(false);
      showToast(result.job_id !== null ? t("upload.startedBackground") : result.reused ? t("upload.reused") : t("upload.draftCreated"));
      reloadDoc();
      setReloadKey((key) => key + 1);
    } catch {
      setUploadError(t("errors.unavailable"));
    } finally {
      setBusy(false);
    }
  }

  function openUpload() {
    setFile(null);
    setLabel("");
    setActivate(false);
    setUploadError(null);
    setUploading(true);
  }

  const back = () => router.push("/admin/documents");

  if (load.state === "loading") return <p className={m.faint}>{t("loading")}</p>;
  if (load.state !== "ready") {
    return (
      <div>
        <p role="alert">{t(load.state === "missing" ? "errors.documentNotFound" : "errors.unavailable")}</p>
        <button className={m.btnSec} onClick={back} type="button">
          {t("versions.backToList")}
        </button>
      </div>
    );
  }

  return (
    <>
      <DocumentVersionsModal
        doc={load.doc}
        key={reloadKey}
        onChanged={reloadDoc}
        onClose={back}
        onUploadNewVersion={openUpload}
        variant="page"
      />

      {uploading ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setUploading(false)} type="button">
                {t("cancel")}
              </button>
              <button className={m.btn} disabled={busy || !file} form="doc-newversion-page" type="submit">
                <CheckCircle2 aria-hidden="true" size={14} /> {t("upload.submit")}
              </button>
            </>
          }
          icon={UploadCloud}
          onClose={() => setUploading(false)}
          subtitle={load.doc.title}
          title={t("newVersion")}
          tone="indigo"
        >
          <form id="doc-newversion-page" onSubmit={submitUpload}>
            <label className={m.drop}>
              <input
                accept=".docx,.pdf,.md,.txt"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
                type="file"
              />
              <UploadCloud aria-hidden="true" size={22} />
              <span>
                <b>{file ? file.name : t("upload.drop")}</b>
                <span>{t("upload.dropHint")}</span>
              </span>
            </label>
            <div className={m.fgrid} style={{ marginTop: 14 }}>
              <div>
                <label htmlFor="pv-ver">{t("upload.version")}</label>
                <input id="pv-ver" onChange={(e) => setLabel(e.target.value)} required type="text" value={label} />
              </div>
              <div>
                <label htmlFor="pv-eff">{t("upload.effectiveFrom")}</label>
                <input id="pv-eff" onChange={(e) => setEffectiveFrom(e.target.value)} type="date" value={effectiveFrom} />
              </div>
            </div>
            <label className={styles.activateRow}>
              <input checked={activate} onChange={(e) => setActivate(e.target.checked)} type="checkbox" />
              <span>
                <b>{t("upload.activateNow")}</b>
                <small>{activate ? t("upload.activateNowHint") : t("upload.draftOnlyHint")}</small>
              </span>
            </label>
            {uploadError ? <p role="alert">{uploadError}</p> : null}
          </form>
        </PortalModal>
      ) : null}
      {toastNode}
    </>
  );
}
