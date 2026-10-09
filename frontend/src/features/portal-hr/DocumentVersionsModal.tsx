"use client";

import {
  AlertTriangle,
  AlignLeft,
  ArrowLeft,
  CheckCircle2,
  Copy,
  FileEdit,
  FileText,
  GitCompare,
  History,
  Pencil,
  PlayCircle,
  RotateCcw,
  Save,
  ScanText,
  Sparkles,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { JobProgress } from "@/components/job-progress/JobProgress";
import { ConfirmModal, modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  DocumentListItemResponseDTO,
  DocumentVersionDetailResponseDTO,
  DocumentVersionResponseDTO,
  DocumentVersionStateDTO,
  JobResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { DocumentReader } from "./DocumentReader";
import styles from "./DocumentVersionsModal.module.scss";
import { PdfViewer } from "./PdfViewer";
import { isJobFinished, useJob } from "./useJob";
import { VersionComparePanel } from "./VersionComparePanel";
import { VersionPicker } from "./VersionPicker";
import { type SaveFormat, WordEditorPanel } from "./WordEditorPanel";

type Translate = (key: string, values?: Record<string, string | number>) => string;

const KNOWN_ERRORS = new Set([
  "VERSION_CONFLICT",
  "VERSION_NOT_EDITABLE",
  "VERSION_LABEL_EXISTS",
  "VERSION_LABEL_REQUIRED",
  "VERSION_LABEL_TOO_LONG",
  "VERSION_CONTENT_TOO_SHORT",
  "VERSION_ALREADY_CURRENT",
  "VERSION_NOT_ACTIVATABLE",
  "VERSION_NOT_DELETABLE",
  "DOCUMENT_ARCHIVED",
]);

/** Khóa dịch của lỗi (dịch lúc hiển thị): hàm `t` của next-intl đổi tham chiếu mỗi lần render nên không đưa vào effect. */
function errorKey(error: unknown): string {
  if (error instanceof PortalError) {
    if (error.apiCode && KNOWN_ERRORS.has(error.apiCode)) return `errors.${error.apiCode}`;
    return `errors.${error.code}`;
  }
  return "errors.unavailable";
}

function formatDay(iso: string | null): string {
  return iso ? new Date(`${iso}T00:00:00`).toLocaleDateString("vi-VN") : "";
}

function effectiveText(t: Translate, v: DocumentVersionResponseDTO): string {
  if (v.effective_from && v.effective_to) {
    return t("effective.range", { from: formatDay(v.effective_from), to: formatDay(v.effective_to) });
  }
  if (v.effective_from) return t("effective.from", { from: formatDay(v.effective_from) });
  return t("effective.none");
}

const ACTIVATE_STATES: DocumentVersionStateDTO[] = ["DRAFT", "SUPERSEDED"];

type ViewTab = "original" | "content" | "compare";

type Confirm = { kind: "activate"; version: DocumentVersionResponseDTO } | { kind: "delete"; version: DocumentVersionResponseDTO };

/** Quản lý phiên bản của một tài liệu (mục 16): xem bản bất kỳ, sao chép thành bản nháp, sửa nháp (khóa lạc quan),
 * kích hoạt chạy nền có phần trăm, đặt lại bản cũ làm bản áp dụng. Bản đang áp dụng và đã thay thế không sửa tại chỗ. */
export function DocumentVersionsModal({
  doc,
  onClose,
  onChanged,
  onUploadNewVersion,
  variant = "modal",
}: {
  doc: DocumentListItemResponseDTO;
  onClose: () => void;
  onChanged: () => void;
  onUploadNewVersion: () => void;
  /** `page`: trang riêng rộng (đường dẫn /admin/documents/[id]); `modal`: cửa sổ nổi như trước. */
  variant?: "modal" | "page";
}) {
  const t = useTranslations("portalDocuments.versions") as unknown as Translate;
  const tt = useTranslations("portalDocuments");

  const [versions, setVersions] = useState<DocumentVersionResponseDTO[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detailState, setDetailState] = useState<{ id: number; data: DocumentVersionDetailResponseDTO } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<Confirm | null>(null);
  const [activateFrom, setActivateFrom] = useState(() => new Date().toISOString().slice(0, 10));

  // Đang sửa đúng phiên bản nào; đổi sang phiên bản khác thì `editing` tự thành false.
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTab, setEditTab] = useState<"write" | "preview">("write");
  // Tab đang chọn theo từng phiên bản (chưa chọn thì mặc định: "Bản gốc" nếu xem được, không thì "Nội dung").
  const [tabByVersion, setTabByVersion] = useState<Record<number, ViewTab>>({});
  // Trình soạn thảo kiểu Word (chỉ khi máy chủ bật `WORD_EDITOR_ENABLED`): đang mở cho phiên bản nào, và đang chờ đồng bộ nội dung.
  const [canWordEdit, setCanWordEdit] = useState(false);
  const [wordEditingId, setWordEditingId] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  // Chỗ trên thanh đầu trang để trình soạn thảo đặt nút Lưu/Xuất/Xong (chỉ trang riêng).
  const [barNode, setBarNode] = useState<HTMLElement | null>(null);
  // Phần người dùng đã sửa của đúng phiên bản đang soạn; chưa sửa trường nào thì lấy nguyên giá trị đang lưu.
  const [draftEdit, setDraftEdit] = useState<{ id: number; markdown?: string; label?: string; effective?: string } | null>(
    null,
  );

  const [jobId, setJobId] = useState<number | null>(null);
  const [finishedJob, setFinishedJob] = useState<JobResponseDTO | null>(null);

  const selected = useMemo(() => versions?.find((v) => v.id === selectedId) ?? null, [versions, selectedId]);
  const detail = detailState !== null && detailState.id === selectedId ? detailState.data : null;
  const wordEditing = wordEditingId !== null && wordEditingId === selectedId;
  const originalName = detail?.version.original_filename.toLowerCase() ?? "";
  // "Bản gốc": PDF mở thẳng; Word được chuyển sang PDF ở máy chủ (cần trình soạn thảo bật); Markdown thì không có bố cục để xem.
  const originalUrl =
    detail === null
      ? null
      : originalName.endsWith(".pdf")
        ? portalHrApi.previewDocumentUrl(detail.version.id)
        : originalName.endsWith(".docx") && canWordEdit
          ? portalHrApi.previewDocumentUrl(detail.version.id)
          : null;
  const viewTab: ViewTab = (selectedId !== null ? tabByVersion[selectedId] : undefined) ?? (originalUrl ? "original" : "content");
  const setViewTab = (tab: ViewTab) => {
    if (selectedId !== null) setTabByVersion((current) => ({ ...current, [selectedId]: tab }));
  };
  const resetTab = (id: number) =>
    setTabByVersion((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
  const editing = (editingId !== null && editingId === selectedId) || wordEditing;
  const overrides = draftEdit !== null && draftEdit.id === selectedId ? draftEdit : null;
  const draftMarkdown = overrides?.markdown ?? detail?.markdown ?? "";
  const draftLabel = overrides?.label ?? detail?.version.version_label ?? "";
  const draftEffective = overrides?.effective ?? detail?.version.effective_from ?? "";

  function patchDraft(patch: { markdown?: string; label?: string; effective?: string }) {
    if (selectedId === null) return;
    setDraftEdit((current) => ({ ...(current?.id === selectedId ? current : {}), id: selectedId, ...patch }));
  }

  const loadVersions = useCallback(
    async (keepSelection?: number | null) => {
      try {
        const result = await portalHrApi.listDocumentVersions(doc.id);
        setVersions(result);
        setSelectedId((current) => {
          const wanted = keepSelection ?? current;
          if (wanted !== null && result.some((v) => v.id === wanted)) return wanted;
          return (result.find((v) => v.state === "CURRENT") ?? result[0])?.id ?? null;
        });
        return result;
      } catch (caught) {
        setError(errorKey(caught));
        return null;
      }
    },
    [doc.id],
  );

  // Mở lại modal giữa lúc một bản đang được kích hoạt: nối lại đúng job để thanh phần trăm tiếp tục chạy.
  useEffect(() => {
    void (async () => {
      const result = await loadVersions();
      const processing = result?.find((v) => v.state === "PROCESSING");
      if (processing) {
        try {
          const jobs = await portalHrApi.listActiveJobs("ACTIVATE_VERSION");
          const job = jobs.find((j) => j.document_version_id === processing.id);
          if (job) setJobId(job.id);
        } catch {
          /* không nối lại được thì thôi, danh sách vẫn hiện trạng thái đang xử lý */
        }
      }
    })();
  }, [loadVersions]);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .getCapabilities()
      .then((result) => !cancelled && setCanWordEdit(result.word_editor))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedId === null) return;
    let cancelled = false;
    portalHrApi
      .getDocumentVersion(doc.id, selectedId)
      .then((result) => !cancelled && setDetailState({ id: selectedId, data: result }))
      .catch((caught: unknown) => !cancelled && setError(errorKey(caught)));
    return () => {
      cancelled = true;
    };
  }, [doc.id, selectedId, versions]);

  const hasProcessing = versions?.some((v) => v.state === "PROCESSING") ?? false;
  useEffect(() => {
    if (!hasProcessing || jobId !== null) return;
    const timer = setInterval(() => void loadVersions(), 4000);
    return () => clearInterval(timer);
  }, [hasProcessing, jobId, loadVersions]);

  const { job, lost } = useJob(jobId, (done) => {
    setFinishedJob(done);
    void loadVersions().then(() => onChanged());
  });
  const activating = jobId !== null && !isJobFinished(job) && !lost;

  async function startActivation(version: DocumentVersionResponseDTO) {
    setBusy(true);
    setError(null);
    setFinishedJob(null);
    try {
      const created = await portalHrApi.activateDocumentVersion(doc.id, version.id, {
        effective_from: activateFrom || null,
      });
      setConfirm(null);
      setJobId(created.id);
      await loadVersions(version.id);
    } catch (caught) {
      setConfirm(null);
      setError(errorKey(caught));
    } finally {
      setBusy(false);
    }
  }

  async function copyVersion(version: DocumentVersionResponseDTO) {
    setBusy(true);
    setError(null);
    try {
      const created = await portalHrApi.copyDocumentVersion(doc.id, version.id, {});
      await loadVersions(created.id);
      onChanged();
      setDraftEdit(null);
      setWordEditingId(null);
      // Có trình soạn thảo Word thì chỉ chọn bản nháp vừa tạo (HR bấm "Soạn thảo Word" để sửa); không thì mở sẵn khung sửa Markdown.
      if (canWordEdit) setEditingId(null);
      else {
        setEditTab("write");
        setEditingId(created.id);
      }
    } catch (caught) {
      setError(errorKey(caught));
    } finally {
      setBusy(false);
    }
  }

  async function removeDraft(version: DocumentVersionResponseDTO) {
    setBusy(true);
    setError(null);
    try {
      await portalHrApi.deleteDocumentVersion(doc.id, version.id);
      setConfirm(null);
      setSelectedId(null);
      await loadVersions(null);
      onChanged();
    } catch (caught) {
      setConfirm(null);
      setError(errorKey(caught));
    } finally {
      setBusy(false);
    }
  }

  /** Đã bấm Lưu trong trình soạn thảo Word: ONLYOFFICE gửi file về backend, backend đọc thành Markdown rồi dựng file gốc theo
   * định dạng đã chọn. Đợi tên file gốc đổi sang đuôi mới (xong bước cuối) rồi mới đọc lại bản nháp. */
  async function finishWordEditing(format: SaveFormat, changed: boolean) {
    const id = wordEditingId;
    setWordEditingId(null);
    if (id === null || !changed) return;
    setSyncing(true);
    const suffix = format === "pdf" ? ".pdf" : format === "docx" ? ".docx" : ".md";
    try {
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        const latest = await portalHrApi.getDocumentVersion(doc.id, id);
        if (latest.version.original_filename.toLowerCase().endsWith(suffix)) break;
      }
    } catch {
      /* không đọc lại được thì thôi, danh sách bên dưới vẫn tải lại */
    } finally {
      await loadVersions(id);
      onChanged();
      resetTab(id);
      setSyncing(false);
    }
  }

  function startEdit() {
    if (!detail) return;
    setDraftEdit(null);
    setEditTab("write");
    setEditingId(detail.version.id);
  }

  async function saveEdit() {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      const body = {
        expected_updated_at: detail.version.updated_at,
        markdown: draftMarkdown !== detail.markdown ? draftMarkdown : null,
        label: draftLabel !== detail.version.version_label ? draftLabel : null,
        effective_from: draftEffective && draftEffective !== detail.version.effective_from ? draftEffective : null,
        clear_effective_from: !draftEffective && detail.version.effective_from !== null,
      };
      const updated = await portalHrApi.updateDocumentVersion(doc.id, detail.version.id, body);
      await loadVersions(updated.id);
      setEditingId(null);
      setDraftEdit(null);
      onChanged();
    } catch (caught) {
      setError(errorKey(caught));
    } finally {
      setBusy(false);
    }
  }

  const structureNote =
    detail?.version.structure_quality === "POOR"
      ? t("structure.POOR")
      : detail?.version.structure_quality === "MEDIUM"
        ? t("structure.MEDIUM")
        : null;

  const isPage = variant === "page";
  const locked = busy || activating || editing || syncing;

  const headActions = (
    <>
      <button className={styles.headBtn} disabled={busy || activating} onClick={onUploadNewVersion} type="button">
        <UploadCloud aria-hidden="true" size={14} /> {t("uploadNew")}
      </button>
      {selected ? (
        <button className={styles.headBtn} disabled={busy || activating} onClick={() => copyVersion(selected)} type="button">
          <Copy aria-hidden="true" size={14} /> {t("copy")}
        </button>
      ) : null}
    </>
  );

  // Nút thao tác của phiên bản đang chọn: cùng kiểu với các trang khác, có chữ; riêng nút xóa trên trang riêng chỉ có biểu tượng.
  const secondaryClass = m.btnSec;
  const primaryClass = m.btn;
  // `collapsible`: trên trang riêng, màn hình hẹp thì chỉ còn biểu tượng (có chú thích) để thanh đầu trang luôn nằm trên một dòng.
  const withLabel = (icon: ReactNode, label: string, iconOnly = false, collapsible = false) =>
    iconOnly ? (
      icon
    ) : (
      <>
        {icon} <span className={collapsible && isPage ? styles.btnText : undefined}>{label}</span>
      </>
    );

  const actionButtons =
    detail && selected ? (
      <>
        {detail.can_edit && !canWordEdit ? (
          <button
            aria-label={t("edit")}
            className={secondaryClass}
            disabled={locked}
            onClick={startEdit}
            title={t("edit")}
            type="button"
          >
            {withLabel(<Pencil aria-hidden="true" size={14} />, t("edit"))}
          </button>
        ) : null}
        {detail.can_edit && canWordEdit ? (
          <button
            className={primaryClass}
            disabled={locked}
            onClick={() => setWordEditingId(detail.version.id)}
            type="button"
          >
            {withLabel(<FileEdit aria-hidden="true" size={14} />, t("wordEditor.open"))}
          </button>
        ) : null}
        {ACTIVATE_STATES.includes(detail.version.state) ? (
          <button
            className={primaryClass}
            disabled={busy || activating || editing}
            onClick={() => setConfirm({ kind: "activate", version: detail.version })}
            title={editing ? t("editor.saveFirst") : undefined}
            type="button"
          >
            {withLabel(
              detail.version.state === "DRAFT" ? (
                <PlayCircle aria-hidden="true" size={14} />
              ) : (
                <RotateCcw aria-hidden="true" size={14} />
              ),
              detail.version.state === "DRAFT" ? t("activate") : t("setCurrent"),
            )}
          </button>
        ) : null}
        {detail.version.state === "DRAFT" ? (
          <button
            aria-label={t("deleteDraft")}
            className={secondaryClass}
            disabled={busy || activating || editing}
            onClick={() => setConfirm({ kind: "delete", version: detail.version })}
            title={editing ? t("editor.saveFirst") : t("deleteDraft")}
            type="button"
          >
            {withLabel(<Trash2 aria-hidden="true" size={14} />, t("deleteDraft"), isPage)}
          </button>
        ) : null}
        <a
          aria-label={tt("viewOriginal")}
          className={secondaryClass}
          href={portalHrApi.originalDocumentUrl(detail.version.id)}
          rel="noopener noreferrer"
          target="_blank"
          title={tt("viewOriginal")}
        >
          {withLabel(<FileText aria-hidden="true" size={14} />, tt("viewOriginal"), false, true)}
        </a>
      </>
    ) : null;

  const errorBanner = error ? (
    <p className={styles.bannerError} role="alert">
      <AlertTriangle aria-hidden="true" size={14} /> {t(error)}
    </p>
  ) : null;

  const progressBlocks = (
    <>
      {jobId !== null && !finishedJob ? (
        <div className={styles.progressBox}>
          <b>{t("progress.title")}</b>
          <JobProgress
            percent={job?.progress_percent ?? 0}
            stage={job?.stage ?? t("progress.waiting")}
            state={job?.status === "FAILED" ? "failed" : job?.status === "SUCCEEDED" ? "done" : "running"}
          />
          {lost ? <small>{t("progress.lost")}</small> : null}
        </div>
      ) : null}
      {finishedJob ? (
        <p className={finishedJob.status === "SUCCEEDED" ? styles.bannerOk : styles.bannerError} role="status">
          {finishedJob.status === "SUCCEEDED" ? (
            <>
              <CheckCircle2 aria-hidden="true" size={14} />{" "}
              {t("progress.done", {
                sections: Number(finishedJob.result?.section_count ?? 0),
                chunks: Number(finishedJob.result?.chunk_count ?? 0),
              })}
              {finishedJob.result?.reused_embeddings ? ` ${t("progress.reused")}` : ""}
            </>
          ) : (
            <>
              <AlertTriangle aria-hidden="true" size={14} /> {t("progress.failed", { error: finishedJob.error ?? "" })}
            </>
          )}
        </p>
      ) : null}
    </>
  );

  const detailBanners = detail ? (
    <>
      {detail.version.failure_reason ? (
        <p className={styles.bannerError}>
          <AlertTriangle aria-hidden="true" size={14} /> {t("lastFailure", { error: detail.version.failure_reason })}
        </p>
      ) : null}
      {detail.version.ocr && detail.version.state === "PROCESSING" ? (
        <p className={styles.bannerInfo}>
          <ScanText aria-hidden="true" size={14} /> {t("ocr.pending")}
        </p>
      ) : null}
      {/* Trang riêng không hiện các ghi chú tư vấn (chất lượng cấu trúc, OCR cần soát, AI đã tách mục…); cửa sổ nổi vẫn giữ. */}
      {isPage ? null : (
        <>
          {structureNote ? (
            <p className={styles.bannerWarn}>
              <AlertTriangle aria-hidden="true" size={14} /> {structureNote}
            </p>
          ) : null}
          {detail.version.ocr && detail.version.state !== "PROCESSING" ? (
            <p className={styles.bannerWarn}>
              <ScanText aria-hidden="true" size={14} /> {t("ocr.review")}
            </p>
          ) : null}
          {detail.version.ai_split === "APPLIED" ? (
            <p className={styles.bannerInfo}>
              <Sparkles aria-hidden="true" size={14} /> {t("structure.aiApplied")}
            </p>
          ) : null}
          {detail.version.original_filename && detail.version.source === "EDITED" ? (
            <p className={styles.hint}>{t("originalNote", { name: detail.version.original_filename })}</p>
          ) : null}
        </>
      )}
      {syncing ? <p className={styles.hint}>{t("wordEditor.syncing")}</p> : null}
    </>
  ) : null;

  const tabButtons = (
    <>
      {originalUrl ? (
        <button aria-selected={viewTab === "original"} onClick={() => setViewTab("original")} role="tab" type="button">
          <FileText aria-hidden="true" size={14} /> {t("compare.tabOriginal")}
        </button>
      ) : null}
      <button aria-selected={viewTab === "content"} onClick={() => setViewTab("content")} role="tab" type="button">
        <AlignLeft aria-hidden="true" size={14} /> {t("compare.tabContent")}
      </button>
      <button aria-selected={viewTab === "compare"} onClick={() => setViewTab("compare")} role="tab" type="button">
        <GitCompare aria-hidden="true" size={14} /> {t("compare.tabCompare")}
      </button>
    </>
  );

  const content = detail ? (
    wordEditing ? (
      <WordEditorPanel
        barTarget={isPage ? barNode : null}
        documentId={doc.id}
        fill={isPage}
        onCancel={() => setWordEditingId(null)}
        onSaved={finishWordEditing}
        versionId={detail.version.id}
      />
    ) : editing ? (
      <div className={styles.editor}>
        <div className={styles.editGrid}>
          <label>
            {t("editor.label")}
            <input maxLength={32} onChange={(e) => patchDraft({ label: e.target.value })} value={draftLabel} />
          </label>
          <label>
            {t("editor.effective")}
            <input onChange={(e) => patchDraft({ effective: e.target.value })} type="date" value={draftEffective} />
          </label>
        </div>
        <div className={styles.tabs} role="tablist">
          <button aria-selected={editTab === "write"} onClick={() => setEditTab("write")} role="tab" type="button">
            {t("editor.write")}
          </button>
          <button aria-selected={editTab === "preview"} onClick={() => setEditTab("preview")} role="tab" type="button">
            {t("editor.preview")}
          </button>
        </div>
        {editTab === "write" ? (
          <textarea
            aria-label={t("editor.markdown")}
            className={styles.textarea}
            onChange={(e) => patchDraft({ markdown: e.target.value })}
            spellCheck={false}
            value={draftMarkdown}
          />
        ) : (
          <div className={styles.previewBox}>
            <DocumentReader compact markdown={draftMarkdown} tocLabel={tt("toc")} />
          </div>
        )}
        <p className={styles.hint}>{t("editor.hint")}</p>
        <div className={styles.actions}>
          <button className={m.btnSec} disabled={busy} onClick={() => setEditingId(null)} type="button">
            {tt("cancel")}
          </button>
          <button className={m.btn} disabled={busy} onClick={saveEdit} type="button">
            <Save aria-hidden="true" size={14} /> {tt("save")}
          </button>
        </div>
      </div>
    ) : (
      <>
        {isPage ? null : (
        <div className={styles.tabs} role="tablist">
          {tabButtons}
        </div>
        )}
        {viewTab === "original" && originalUrl ? (
          <div className={isPage ? styles.originalFrame : styles.originalFrameModal}>
            <PdfViewer label={t("compare.tabOriginal")} url={originalUrl} />
          </div>
        ) : viewTab === "compare" ? (
          <div className={isPage ? styles.pageScroll : undefined}>
            <VersionComparePanel documentId={doc.id} key={detail.version.id} versionId={detail.version.id} />
          </div>
        ) : (
          <DocumentReader fill={isPage} markdown={detail.markdown} tocLabel={tt("toc")} />
        )}
      </>
    )
  ) : (
    <p className={m.faint}>{tt("loading")}</p>
  );

  const metaText = detail
    ? `${effectiveText(t, detail.version)} · ${t("originalFile", { name: detail.version.original_filename })}${
        detail.version.parent_version_id
          ? ` · ${t("fromParent", {
              label: versions?.find((v) => v.id === detail.version.parent_version_id)?.version_label ?? "…",
            })}`
          : ""
      }`
    : "";

  const modalBody = (
    <>
      {errorBanner}
      <div className={styles.layout}>
        <aside aria-label={t("listLabel")} className={styles.list}>
          {versions === null ? (
            <p className={m.faint}>{tt("loading")}</p>
          ) : (
            versions.map((v) => (
              <button
                className={`${styles.vcard} ${v.id === selectedId ? styles.vcardOn : ""}`}
                key={v.id}
                onClick={() => setSelectedId(v.id)}
                type="button"
              >
                <span className={styles.vtop}>
                  <b>{v.version_label}</b>
                  <i className={styles.chip} data-state={v.state}>
                    {t(`state.${v.state}`)}
                  </i>
                </span>
                <small>{effectiveText(t, v)}</small>
                <small>
                  {t(`source.${v.source}`)}
                  {v.uploaded_by_name ? ` · ${v.uploaded_by_name}` : ""}
                  {v.task_count > 0 ? ` · ${t("tasks", { count: v.task_count })}` : ""}
                </small>
              </button>
            ))
          )}
        </aside>

        <section className={styles.pane}>
          {progressBlocks}
          {detail && selected ? (
            <>
              <div className={styles.paneHead}>
                <div>
                  <h3>
                    {detail.version.version_label}{" "}
                    <i className={styles.chip} data-state={detail.version.state}>
                      {t(`state.${detail.version.state}`)}
                    </i>
                  </h3>
                  <small>{metaText}</small>
                </div>
                <div className={styles.actions}>{actionButtons}</div>
              </div>
              {detailBanners}
              {content}
            </>
          ) : (
            <p className={m.faint}>{tt("loading")}</p>
          )}
        </section>
      </div>
    </>
  );

  // Trang riêng: một thanh đầu trang duy nhất (quay lại, tên + hiệu lực, chọn phiên bản, tab, thao tác); còn lại dành hết cho nội dung.
  const pageTabs = (
    <div className={styles.segment} role="tablist">
      {tabButtons}
    </div>
  );

  const pageBody = (
    <div className={styles.pageShell}>
      <div className={styles.pageBar}>
        <button
          aria-label={t("backToList")}
          className={styles.backIcon}
          onClick={onClose}
          title={t("backToList")}
          type="button"
        >
          <ArrowLeft aria-hidden="true" size={16} />
        </button>
        <div className={styles.barTitle}>
          <h1 title={doc.title}>{doc.title}</h1>
          <small>{metaText}</small>
        </div>
        {versions ? (
          <VersionPicker
            effectiveLabel={(v) => effectiveText(t, v)}
            label={t("listLabel")}
            onSelect={setSelectedId}
            selectedId={selectedId}
            stateLabel={(v) => t(`state.${v.state}`)}
            versions={versions}
          />
        ) : null}
        {wordEditing ? null : pageTabs}
        <span className={styles.barSpacer} />
        <div className={styles.barActions}>
          {wordEditing ? (
            <div className={styles.barEditor} ref={setBarNode} />
          ) : (
            <>
              <button
                className={m.btnSec}
                disabled={busy || activating}
                onClick={onUploadNewVersion}
                title={t("uploadNew")}
                type="button"
              >
                <UploadCloud aria-hidden="true" size={14} /> <span className={styles.btnText}>{t("uploadShort")}</span>
              </button>
              {selected ? (
                <button
                  className={m.btnSec}
                  disabled={busy || activating}
                  onClick={() => copyVersion(selected)}
                  title={t("copy")}
                  type="button"
                >
                  <Copy aria-hidden="true" size={14} /> <span className={styles.btnText}>{t("copyShort")}</span>
                </button>
              ) : null}
              {actionButtons}
            </>
          )}
        </div>
      </div>
      {errorBanner}
      {progressBlocks}
      {detailBanners}
      <div className={styles.pageMain}>{content}</div>
    </div>
  );

  return (
    <>
      {isPage ? (
        pageBody
      ) : (
        <PortalModal
          closeLabel={tt("close")}
          footer={
            <button className={m.btnSec} onClick={onClose} type="button">
              {tt("closeButton")}
            </button>
          }
          headerActions={headActions}
          icon={History}
          onClose={onClose}
          subtitle={t("subtitle", { count: versions?.length ?? doc.version_count })}
          title={doc.title}
          tone="indigo"
          vwide
        >
          {modalBody}
        </PortalModal>
      )}

      {confirm?.kind === "activate" ? (
        <PortalModal
          closeLabel={tt("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setConfirm(null)} type="button">
                {tt("cancel")}
              </button>
              <button className={m.btn} disabled={busy} onClick={() => startActivation(confirm.version)} type="button">
                <PlayCircle aria-hidden="true" size={14} />{" "}
                {confirm.version.state === "SUPERSEDED" ? t("setCurrent") : t("activate")}
              </button>
            </>
          }
          icon={PlayCircle}
          onClose={() => setConfirm(null)}
          title={t("confirm.activateTitle", { label: confirm.version.version_label })}
          tone="indigo"
        >
          <p className={styles.confirmText}>
            {confirm.version.state === "SUPERSEDED"
              ? t("confirm.setCurrentBody", { label: confirm.version.version_label })
              : t("confirm.activateBody", { label: confirm.version.version_label })}
          </p>
          <label className={styles.confirmDate}>
            {t("confirm.effectiveFrom")}
            <input onChange={(e) => setActivateFrom(e.target.value)} type="date" value={activateFrom} />
          </label>
        </PortalModal>
      ) : null}

      {confirm?.kind === "delete" ? (
        <ConfirmModal
          body={t("confirm.deleteBody")}
          busy={busy}
          cancelLabel={tt("cancel")}
          closeLabel={tt("close")}
          confirmIcon={Trash2}
          confirmLabel={t("deleteDraft")}
          danger
          icon={Trash2}
          onCancel={() => setConfirm(null)}
          onConfirm={() => removeDraft(confirm.version)}
          title={t("confirm.deleteTitle", { label: confirm.version.version_label })}
        />
      ) : null}
    </>
  );
}
