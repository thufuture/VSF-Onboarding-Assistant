"use client";

import {
  Archive,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  ChevronDown,
  FileText,
  History,
  Link2,
  ListChecks,
  Pencil,
  RotateCcw,
  Search,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { JobProgress } from "@/components/job-progress/JobProgress";
import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type { DocumentTaskChoiceDTO } from "@/features/portal-hr/dto/requestDTO/portal.request";
import type {
  DocumentCategoryResponseDTO,
  DocumentListItemResponseDTO,
  JobResponseDTO,
  StageDraftChangeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";
import { useRouter } from "@/i18n/navigation";

import { CategoryPicker } from "./CategoryPicker";
import { categoryFlat, categoryStyle, type DocTone } from "./docCategory";
import { DocumentRemovalModal } from "./DocumentRemovalModal";
import { StageApplyPrompt } from "./StageApplyPrompt";
import styles from "./DocumentsListPage.module.scss";
import { isJobFinished, useActiveActivations, useJob } from "./useJob";

const PAGE_SIZE = 6;
// Chiều cao tối thiểu của vùng bảng = đủ một trang đầy, để chân phân trang luôn nằm đáy thẻ.
const ROW_HEIGHT = 64;
const HEAD_HEIGHT = 41;

const API_ERROR_KEYS: Record<string, string> = {
  INGEST_FAILED: "errors.ingestFailed",
  CATEGORY_NOT_FOUND: "errors.categoryNotFound",
  DOCUMENT_PROCESSING: "errors.documentProcessing",
  TASK_CHOICE_REQUIRED: "errors.taskChoiceRequired",
  DOCUMENT_NOT_FOUND: "errors.documentNotFound",
};

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) {
    const mapped = error.apiCode ? API_ERROR_KEYS[error.apiCode] : undefined;
    return t(mapped ?? `errors.${error.code}`);
  }
  return t("errors.unavailable");
}

/** Ngày (yyyy-mm-dd) theo giờ máy người xem, để so với ô chọn ngày. */
function localDay(iso: string): string {
  return new Date(iso).toLocaleDateString("sv-SE");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN");
}

type FilterOption = { value: string; label: string; hint?: string; icon?: ReactNode; tone?: DocTone };

/** Ô lọc dạng thả xuống: mỗi ô một tông màu riêng, mỗi lựa chọn có icon màu theo ý nghĩa (v15: .doc-filter-*). */
function FilterDrop({
  label,
  icon,
  tone,
  value,
  options,
  open,
  onToggle,
  onPick,
}: {
  label: string;
  icon: ReactNode;
  tone: DocTone;
  value: string;
  options: FilterOption[];
  open: boolean;
  onToggle: () => void;
  onPick: (value: string) => void;
}) {
  const current = options.find((o) => o.value === value) ?? options[0];
  return (
    <div className={styles.drop}>
      <button
        aria-expanded={open}
        className={`${styles.dropTrigger} ${styles[`drop_${tone}`]} ${value ? styles.dropActive : ""}`}
        onClick={onToggle}
        type="button"
      >
        <span className={styles.dropIcon}>{icon}</span>
        <span className={styles.dropText}>
          <small>{label}</small>
          <b>{current.label}</b>
        </span>
        <ChevronDown aria-hidden="true" className={open ? styles.dropCaretOpen : ""} size={13} />
      </button>
      {open ? (
        <div className={styles.dropMenu}>
          {options.map((o) => (
            <button
              className={o.value === value ? styles.dropOn : ""}
              key={o.value}
              onClick={() => onPick(o.value)}
              type="button"
            >
              {o.icon ? <i className={`${styles.optIcon} ${styles[`tone_${o.tone ?? "slate"}`]}`}>{o.icon}</i> : null}
              <span>
                <b>{o.label}</b>
                {o.hint ? <small>{o.hint}</small> : null}
              </span>
              {o.value === value ? <Check aria-hidden="true" size={14} /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

type Modal =
  | { kind: "upload" }
  | { kind: "newVersion"; doc: DocumentListItemResponseDTO }
  | { kind: "edit"; doc: DocumentListItemResponseDTO }
  | { kind: "archive"; doc: DocumentListItemResponseDTO }
  | { kind: "delete"; doc: DocumentListItemResponseDTO }
  | { kind: "reactivate"; doc: DocumentListItemResponseDTO }
  | { kind: "applyDrafts"; changes: StageDraftChangeResponseDTO[] };

/** "Tài liệu nguồn" thật — cổng bố cục và flow modal của prototype v15 (thêm / xem mục lục / sửa / phiên bản mới /
 * ngừng sử dụng có xác nhận / kích hoạt lại). "Xóa" của v15 được thay bằng chuyển trạng thái ARCHIVED để giữ lịch sử ingest. */
export function DocumentsListPage() {
  const t = useTranslations("portalDocuments");
  const router = useRouter();
  const [toastNode, showToast] = useToast();

  const [documents, setDocuments] = useState<DocumentListItemResponseDTO[] | null>(null);
  const [categories, setCategories] = useState<DocumentCategoryResponseDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal | null>(null);
  const [busy, setBusy] = useState(false);

  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [usageFilter, setUsageFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [openFilter, setOpenFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const [file, setFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [docCategory, setDocCategory] = useState("");
  const [docVersion, setDocVersion] = useState("1.0");
  const [docEffectiveFrom, setDocEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));

  // "Tải và kích hoạt luôn" (tài liệu mới) hay chỉ tạo bản nháp để xem lại rồi mới kích hoạt (phiên bản mới).
  const [docActivate, setDocActivate] = useState(true);
  const [uploadJobId, setUploadJobId] = useState<number | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const { jobs: activeJobs, refresh: refreshJobs } = useActiveActivations(true, () => reload());
  const uploadJob = useJob(uploadJobId, () => {
    reload();
    refreshJobs();
  });

  function reload() {
    portalHrApi
      .listDocuments()
      .then((result) => setDocuments(result))
      .catch((caught: unknown) => setError(errorMessage(t, caught)));
  }

  useEffect(() => {
    reload();
    portalHrApi
      .listDocumentCategories()
      .then((result) => {
        setCategories(result);
        setDocCategory((current) => current || (result[0]?.slug ?? ""));
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Mô tả ngắn của hai nhóm tài liệu hiện có (nhóm khác không có mô tả thì chỉ hiện tên).
  const categoryHints: Record<string, string> = {
    onboarding: t("category.hint.onboarding"),
    "tai-lieu-khac": t("category.hint.other"),
  };

  const categoryNames = useMemo(
    () => Array.from(new Set((documents ?? []).map((d) => d.category_name))).sort(),
    [documents],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (documents ?? []).filter(
      (d) =>
        (!q ||
          d.title.toLowerCase().includes(q) ||
          (d.owner_name ?? "").toLowerCase().includes(q) ||
          d.task_titles.some((task) => task.toLowerCase().includes(q))) &&
        (!usageFilter || (usageFilter === "used" ? d.task_titles.length > 0 : d.task_titles.length === 0)) &&
        (!statusFilter || d.status === statusFilter) &&
        (!categoryFilter || d.category_name === categoryFilter) &&
        (!fromDate || localDay(d.updated_at) >= fromDate) &&
        (!toDate || localDay(d.updated_at) <= toDate),
    );
  }, [documents, query, statusFilter, categoryFilter, usageFilter, fromDate, toDate]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const total = documents?.length ?? 0;
  const readyCount = documents?.filter((d) => d.status === "ACTIVE").length ?? 0;
  const pendingCount = documents?.filter((d) => d.status !== "ACTIVE").length ?? 0;
  const usedCount = documents?.filter((d) => d.task_titles.length > 0).length ?? 0;

  function openUpload() {
    setFile(null);
    setDocTitle("");
    setDocVersion("1.0");
    setDocActivate(true);
    setModal({ kind: "upload" });
  }

  function openNewVersion(doc: DocumentListItemResponseDTO) {
    setFile(null);
    setDocVersion("");
    setDocActivate(false);
    setModal({ kind: "newVersion", doc });
  }

  function openEdit(doc: DocumentListItemResponseDTO) {
    setDocTitle(doc.title);
    setDocCategory(doc.category_slug);
    setModal({ kind: "edit", doc });
  }

  function openView(doc: DocumentListItemResponseDTO) {
    router.push(`/admin/documents/${doc.id}`);
  }

  async function submitUpload(event: FormEvent, existing?: DocumentListItemResponseDTO) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setWarning(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("version_label", docVersion);
      if (existing) {
        // Thêm phiên bản mới cho tài liệu đã có: gửi mã tài liệu, không gửi lại tên/danh mục.
        form.append("document_id", String(existing.id));
      } else {
        form.append("title", docTitle);
        form.append("category_slug", docCategory);
        form.append("source_key", `portal-${Date.now()}`);
      }
      if (docEffectiveFrom) form.append("effective_from", docEffectiveFrom);
      if (docActivate) form.append("activate", "true");
      const result = await portalHrApi.uploadDocument(form);
      setModal(null);
      if (result.structure_quality === "POOR") setWarning(t("upload.structurePoor"));
      else if (result.structure_quality === "MEDIUM") setWarning(t("upload.structureMedium"));
      if (result.job_id !== null) {
        setUploadJobId(result.job_id);
        refreshJobs();
        showToast(t("upload.startedBackground"));
      } else {
        showToast(result.reused ? t("upload.reused") : t("upload.draftCreated"));
      }
      reload();
    } catch (caught) {
      setError(errorMessage(t, caught));
      setModal(null);
    } finally {
      setBusy(false);
    }
  }

  async function submitEdit(event: FormEvent) {
    event.preventDefault();
    if (modal?.kind !== "edit") return;
    setError(null);
    setBusy(true);
    try {
      await portalHrApi.updateDocument(modal.doc.id, { title: docTitle, category_slug: docCategory });
      setModal(null);
      showToast(t("notice.updated"));
      reload();
    } catch (caught) {
      setError(errorMessage(t, caught));
      setModal(null);
    } finally {
      setBusy(false);
    }
  }

  /** Xóa/tắt xong: nếu việc xóa task đã được ghi vào bản nháp của ngày nào thì hỏi HR có cập nhật cho nhân viên không. */
  function afterRemoval(changes: StageDraftChangeResponseDTO[], message: string) {
    if (changes.length > 0) {
      setModal({ kind: "applyDrafts", changes });
      return;
    }
    setModal(null);
    showToast(message);
  }

  async function confirmDelete(doc: DocumentListItemResponseDTO, tasks: DocumentTaskChoiceDTO | undefined) {
    setError(null);
    setBusy(true);
    try {
      const result = await portalHrApi.deleteDocument(doc.id, tasks);
      afterRemoval(result.stages_changed, t("notice.deleted"));
      reload();
    } catch (caught) {
      setError(errorMessage(t, caught));
      setModal(null);
    } finally {
      setBusy(false);
    }
  }

  async function confirmStatus(
    doc: DocumentListItemResponseDTO,
    next: "ACTIVE" | "ARCHIVED",
    tasks?: DocumentTaskChoiceDTO,
  ) {
    setError(null);
    setBusy(true);
    try {
      const result = await portalHrApi.setDocumentStatus(doc.id, { status: next, tasks });
      afterRemoval(result.stages_changed ?? [], next === "ARCHIVED" ? t("notice.archived") : t("notice.reactivated"));
      reload();
    } catch (caught) {
      setError(errorMessage(t, caught));
      setModal(null);
    } finally {
      setBusy(false);
    }
  }

  // Phần trăm của job kích hoạt đang chạy theo từng phiên bản (để dòng tài liệu hiện "Đang xử lý 45%").
  const jobByVersion = new Map<number, JobResponseDTO>();
  for (const job of activeJobs) if (job.document_version_id !== null) jobByVersion.set(job.document_version_id, job);

  return (
    <div className={styles.page}>
      <header className={styles.pagehead}>
        <span className={styles.phi}>
          <BookOpen aria-hidden="true" size={22} />
        </span>
        <div className={styles.pageheadText}>
          <h1>{t("title")}</h1>
          <p>{t("description")}</p>
        </div>
        <button className={styles.btn} onClick={openUpload} type="button">
          <UploadCloud aria-hidden="true" size={14} /> {t("addDocument")}
        </button>
      </header>

      {error ? <p className={styles.banner + " " + styles.bannerError}>{error}</p> : null}
      {warning ? <p className={styles.banner + " " + styles.bannerWarn}>{warning}</p> : null}
      {uploadJobId !== null && uploadJob.job && !(isJobFinished(uploadJob.job) && uploadJob.job.status === "SUCCEEDED") ? (
        <div className={styles.jobBox}>
          <b>{uploadJob.job.status === "FAILED" ? t("upload.failedBackground") : t("upload.progressTitle")}</b>
          <JobProgress
            percent={uploadJob.job.progress_percent}
            stage={uploadJob.job.status === "FAILED" ? uploadJob.job.error : uploadJob.job.stage}
            state={uploadJob.job.status === "FAILED" ? "failed" : "running"}
          />
        </div>
      ) : null}

      <div className={styles.kpiGrid}>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.total")}</small>
            <span className={`${styles.ichip} ${styles.toneBlue}`}>
              <FlatIcon name="book" size={22} tone="blue" />
            </span>
          </div>
          <b>{total}</b>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.ready")}</small>
            <span className={`${styles.ichip} ${styles.toneTeal}`}>
              <FlatIcon name="check" size={22} tone="green" />
            </span>
          </div>
          <b>{readyCount}</b>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.pending")}</small>
            <span className={`${styles.ichip} ${styles.toneAmber}`}>
              <FlatIcon name="clock" size={22} tone="amber" />
            </span>
          </div>
          <b>{pendingCount}</b>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.used")}</small>
            <span className={`${styles.ichip} ${styles.toneIndigo}`}>
              <FlatIcon name="tasks" size={22} tone="indigo" />
            </span>
          </div>
          <b>{usedCount}</b>
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles.filterBar}>
          <div className={styles.search}>
            <Search aria-hidden="true" size={14} />
            <input
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              placeholder={t("searchPlaceholder")}
              value={query}
            />
          </div>
          <div className={styles.dateRange}>
            <label className={styles.dateField}>
              <FlatIcon name="clock" size={20} tone="amber" />
              <span>
                <small>{t("filter.from")}</small>
                <input
                  aria-label={t("filter.from")}
                  max={toDate || undefined}
                  onChange={(event) => {
                    setFromDate(event.target.value);
                    setPage(1);
                  }}
                  type="date"
                  value={fromDate}
                />
              </span>
            </label>
            <label className={styles.dateField}>
              <FlatIcon name="clock" size={20} tone="teal" />
              <span>
                <small>{t("filter.to")}</small>
                <input
                  aria-label={t("filter.to")}
                  min={fromDate || undefined}
                  onChange={(event) => {
                    setToDate(event.target.value);
                    setPage(1);
                  }}
                  type="date"
                  value={toDate}
                />
              </span>
            </label>
            {fromDate || toDate ? (
              <button
                className={styles.dateClear}
                onClick={() => {
                  setFromDate("");
                  setToDate("");
                  setPage(1);
                }}
                type="button"
              >
                {t("filter.clearDates")}
              </button>
            ) : null}
          </div>
          <div className={styles.dropRow}>
            <FilterDrop
              icon={<CheckCircle2 aria-hidden="true" size={15} />}
              label={t("filter.status")}
              onPick={(v) => {
                setStatusFilter(v);
                setPage(1);
                setOpenFilter(null);
              }}
              onToggle={() => setOpenFilter(openFilter === "status" ? null : "status")}
              open={openFilter === "status"}
              options={[
                { value: "", label: t("filterAllStatus"), hint: t("filter.statusAllHint"), icon: <ListChecks aria-hidden="true" size={13} />, tone: "slate" },
                { value: "ACTIVE", label: t("status.ACTIVE"), hint: t("filter.activeHint"), icon: <CheckCircle2 aria-hidden="true" size={13} />, tone: "teal" },
                { value: "ARCHIVED", label: t("status.ARCHIVED"), hint: t("filter.archivedHint"), icon: <Clock aria-hidden="true" size={13} />, tone: "amber" },
              ]}
              tone="blue"
              value={statusFilter}
            />
            <FilterDrop
              icon={<Link2 aria-hidden="true" size={15} />}
              label={t("filter.usage")}
              onPick={(v) => {
                setUsageFilter(v);
                setPage(1);
                setOpenFilter(null);
              }}
              onToggle={() => setOpenFilter(openFilter === "usage" ? null : "usage")}
              open={openFilter === "usage"}
              options={[
                { value: "", label: t("filter.usageAll"), hint: t("filter.usageAllHint"), icon: <FileText aria-hidden="true" size={13} />, tone: "slate" },
                { value: "used", label: t("filter.usageUsed"), hint: t("filter.usageUsedHint"), icon: <Link2 aria-hidden="true" size={13} />, tone: "indigo" },
                { value: "unused", label: t("filter.usageUnused"), hint: t("filter.usageUnusedHint"), icon: <FileText aria-hidden="true" size={13} />, tone: "amber" },
              ]}
              tone="indigo"
              value={usageFilter}
            />
            <FilterDrop
              icon={<ListChecks aria-hidden="true" size={15} />}
              label={t("filter.category")}
              onPick={(v) => {
                setCategoryFilter(v);
                setPage(1);
                setOpenFilter(null);
              }}
              onToggle={() => setOpenFilter(openFilter === "category" ? null : "category")}
              open={openFilter === "category"}
              options={[
                { value: "", label: t("filterAllCategory"), icon: <ListChecks aria-hidden="true" size={13} />, tone: "slate" },
                ...categoryNames.map((c) => {
                  const cat = categoryStyle(c, 13);
                  return { value: c, label: c, icon: cat.icon, tone: cat.tone };
                }),
              ]}
              tone="teal"
              value={categoryFilter}
            />
          </div>
        </div>

        <div className={styles.tableWrap} style={{ minHeight: PAGE_SIZE * ROW_HEIGHT + HEAD_HEIGHT }}>
          <table className={styles.table}>
            <colgroup>
              <col style={{ width: "24%" }} />
              <col style={{ width: "13%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "11%" }} />
              <col style={{ width: "11%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "14%" }} />
            </colgroup>
            <thead>
              <tr>
                <th>{t("table.document")}</th>
                <th>{t("table.category")}</th>
                <th>{t("table.sections")}</th>
                <th>{t("table.version")}</th>
                <th>{t("table.status")}</th>
                <th>{t("table.tasks")}</th>
                <th>{t("table.updated")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {documents === null ? (
                <tr>
                  <td colSpan={8}>{t("loading")}</td>
                </tr>
              ) : pageItems.length === 0 ? (
                <tr>
                  <td colSpan={8}>{t("empty")}</td>
                </tr>
              ) : (
                pageItems.map((doc) => {
                  const cat = categoryStyle(doc.category_name);
                  const flat = categoryFlat(doc.category_name);
                  return (
                    <tr className={doc.status !== "ACTIVE" ? styles.rowOff : ""} key={doc.id}>
                      <td>
                        <div className={styles.docName}>
                          <span className={styles.docIcon}>
                            <FlatIcon name={flat.icon} size={24} tone={flat.tone} />
                          </span>
                          <div>
                            <b title={doc.title}>{doc.title}</b>
                            {doc.source_key ? <small title={doc.source_key}>{doc.source_key}</small> : null}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`${styles.kind} ${styles[`tone_${cat.tone}`]}`} title={doc.category_name}>
                          <FlatIcon name={flat.icon} size={16} tone={flat.tone} />
                          <span>{doc.category_name}</span>
                        </span>
                      </td>
                      <td>
                        <div className={styles.process}>
                          <b>{t("sectionCount", { count: doc.section_count })}</b>
                          <small>
                            <CheckCircle2 aria-hidden="true" size={11} /> {t("parsedIngested")}
                          </small>
                        </div>
                      </td>
                      <td>
                        <div className={styles.date}>
                          <b>{doc.current_version_label ?? t("version.none")}</b>
                          <small>
                            {t("version.count", { count: doc.version_count })}
                            {doc.draft_count > 0 ? ` · ${t("version.drafts", { count: doc.draft_count })}` : ""}
                          </small>
                        </div>
                      </td>
                      <td>
                        {doc.processing_version_ids.some((id) => jobByVersion.has(id)) ? (
                          <div className={styles.rowProgress}>
                            {doc.processing_version_ids.map((id) => {
                              const job = jobByVersion.get(id);
                              return job ? (
                                <JobProgress compact key={id} percent={job.progress_percent} stage={job.stage} state="running" />
                              ) : null;
                            })}
                          </div>
                        ) : (
                          <span className={styles.status} data-status={doc.status}>
                            <i />
                            {doc.status === "ACTIVE" && doc.latest_version_id === null
                              ? t("status.NO_CURRENT")
                              : t(`status.${doc.status}`)}
                          </span>
                        )}
                      </td>
                      <td>
                        <div className={styles.used}>
                          {doc.task_titles.length ? (
                            <>
                              {doc.task_titles.slice(0, 2).map((title) => (
                                <span key={title} title={title}>
                                  {title}
                                </span>
                              ))}
                              {doc.task_titles.length > 2 ? (
                                <small>{t("moreTasks", { count: doc.task_titles.length - 2 })}</small>
                              ) : null}
                            </>
                          ) : (
                            <em>{t("noTasks")}</em>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className={styles.date}>
                          <b>{formatDate(doc.updated_at)}</b>
                          {doc.owner_name ? <small title={doc.owner_name}>{doc.owner_name}</small> : null}
                        </div>
                      </td>
                      <td>
                        <div className={styles.rowActions}>
                          <button
                            className={`${styles.iconBtn} ${styles.iconBlue}`}
                            onClick={() => openView(doc)}
                            title={t("view")}
                            type="button"
                          >
                            <History aria-hidden="true" size={13} />
                          </button>
                          <button className={styles.iconBtn} onClick={() => openEdit(doc)} title={t("edit")} type="button">
                            <Pencil aria-hidden="true" size={13} />
                          </button>
                          <button
                            className={`${styles.iconBtn} ${styles.iconAmber}`}
                            onClick={() => openNewVersion(doc)}
                            title={t("newVersion")}
                            type="button"
                          >
                            <UploadCloud aria-hidden="true" size={13} />
                          </button>
                          {doc.status === "ACTIVE" ? (
                            <button
                              className={`${styles.iconBtn} ${styles.iconDanger}`}
                              onClick={() => setModal({ kind: "archive", doc })}
                              title={t("archive")}
                              type="button"
                            >
                              <Archive aria-hidden="true" size={13} />
                            </button>
                          ) : (
                            <button
                              className={`${styles.iconBtn} ${styles.iconOk}`}
                              onClick={() => setModal({ kind: "reactivate", doc })}
                              title={t("reactivate")}
                              type="button"
                            >
                              <RotateCcw aria-hidden="true" size={13} />
                            </button>
                          )}
                          <button
                            className={`${styles.iconBtn} ${styles.iconDanger}`}
                            onClick={() => setModal({ kind: "delete", doc })}
                            title={t("delete")}
                            type="button"
                          >
                            <Trash2 aria-hidden="true" size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className={styles.pager}>
          <span>
            {t("pagerLabel", {
              from: filtered.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1,
              to: Math.min(page * PAGE_SIZE, filtered.length),
              total: filtered.length,
            })}
          </span>
          <div className={styles.pagerButtons}>
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} type="button">
              ‹
            </button>
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
              <button className={p === page ? styles.pagerOn : ""} key={p} onClick={() => setPage(p)} type="button">
                {p}
              </button>
            ))}
            <button disabled={page >= pageCount} onClick={() => setPage((p) => p + 1)} type="button">
              ›
            </button>
          </div>
        </div>
      </div>

      {modal?.kind === "upload" ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("cancel")}
              </button>
              <button className={m.btn} disabled={busy || !file} form="doc-upload" type="submit">
                <CheckCircle2 aria-hidden="true" size={14} /> {t("upload.submit")}
              </button>
            </>
          }
          icon={UploadCloud}
          onClose={() => setModal(null)}
          title={t("upload.title")}
          tone="indigo"
        >
          <form id="doc-upload" onSubmit={(event) => submitUpload(event)}>
            <label className={m.drop}>
              <input
                accept=".docx,.pdf,.md,.txt"
                onChange={(event) => {
                  const picked = event.target.files?.[0] ?? null;
                  setFile(picked);
                  if (picked && !docTitle) setDocTitle(picked.name.replace(/\.[^.]+$/, ""));
                }}
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
              <div className={m.span2}>
                <label htmlFor="up-title">{t("upload.name")}</label>
                <input id="up-title" onChange={(e) => setDocTitle(e.target.value)} required type="text" value={docTitle} />
              </div>
              <div>
                <label htmlFor="up-cat">{t("upload.category")}</label>
                <CategoryPicker hints={categoryHints} id="up-cat" onChange={setDocCategory} options={categories} value={docCategory} />
              </div>
              <div>
                <label htmlFor="up-ver">{t("upload.version")}</label>
                <input id="up-ver" onChange={(e) => setDocVersion(e.target.value)} required type="text" value={docVersion} />
              </div>
              <div>
                <label htmlFor="up-eff">{t("upload.effectiveFrom")}</label>
                <input
                  id="up-eff"
                  onChange={(e) => setDocEffectiveFrom(e.target.value)}
                  type="date"
                  value={docEffectiveFrom}
                />
              </div>
            </div>
            <label className={styles.activateRow}>
              <input checked={docActivate} onChange={(e) => setDocActivate(e.target.checked)} type="checkbox" />
              <span>
                <b>{t("upload.activateNow")}</b>
                <small>{docActivate ? t("upload.activateNowHint") : t("upload.draftOnlyHint")}</small>
              </span>
            </label>
          </form>
        </PortalModal>
      ) : null}

      {modal?.kind === "newVersion" ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("cancel")}
              </button>
              <button className={m.btn} disabled={busy || !file} form="doc-newversion" type="submit">
                <CheckCircle2 aria-hidden="true" size={14} /> {t("upload.submit")}
              </button>
            </>
          }
          icon={UploadCloud}
          onClose={() => setModal(null)}
          subtitle={modal.doc.title}
          title={t("newVersion")}
          tone="indigo"
        >
          <form id="doc-newversion" onSubmit={(event) => submitUpload(event, modal.doc)}>
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
                <label htmlFor="nv-ver">{t("upload.version")}</label>
                <input id="nv-ver" onChange={(e) => setDocVersion(e.target.value)} required type="text" value={docVersion} />
              </div>
              <div>
                <label htmlFor="nv-eff">{t("upload.effectiveFrom")}</label>
                <input
                  id="nv-eff"
                  onChange={(e) => setDocEffectiveFrom(e.target.value)}
                  type="date"
                  value={docEffectiveFrom}
                />
              </div>
            </div>
            <label className={styles.activateRow}>
              <input checked={docActivate} onChange={(e) => setDocActivate(e.target.checked)} type="checkbox" />
              <span>
                <b>{t("upload.activateNow")}</b>
                <small>{docActivate ? t("upload.activateNowHint") : t("upload.draftOnlyHint")}</small>
              </span>
            </label>
          </form>
        </PortalModal>
      ) : null}

      {modal?.kind === "edit" ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("cancel")}
              </button>
              <button className={m.btn} disabled={busy} form="doc-edit" type="submit">
                <CheckCircle2 aria-hidden="true" size={14} /> {t("save")}
              </button>
            </>
          }
          icon={Pencil}
          onClose={() => setModal(null)}
          title={t("editTitle")}
        >
          <form id="doc-edit" onSubmit={submitEdit}>
            <div className={m.fgrid}>
              <div className={m.span2}>
                <label htmlFor="ed-title">{t("upload.name")}</label>
                <input id="ed-title" onChange={(e) => setDocTitle(e.target.value)} required type="text" value={docTitle} />
              </div>
              <div className={m.span2}>
                <label htmlFor="ed-cat">{t("upload.category")}</label>
                <CategoryPicker hints={categoryHints} id="ed-cat" onChange={setDocCategory} options={categories} value={docCategory} />
              </div>
            </div>
          </form>
        </PortalModal>
      ) : null}

      {modal?.kind === "archive" ? (
        <DocumentRemovalModal
          busy={busy}
          doc={modal.doc}
          mode="archive"
          onCancel={() => setModal(null)}
          onConfirm={(tasks) => confirmStatus(modal.doc, "ARCHIVED", tasks)}
        />
      ) : null}

      {modal?.kind === "delete" ? (
        <DocumentRemovalModal
          busy={busy}
          doc={modal.doc}
          mode="delete"
          onCancel={() => setModal(null)}
          onConfirm={(tasks) => confirmDelete(modal.doc, tasks)}
        />
      ) : null}

      {modal?.kind === "reactivate" ? (
        <ConfirmModal
          body={t("reactivateConfirmBody")}
          busy={busy}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={RotateCcw}
          confirmLabel={t("reactivateConfirmButton")}
          icon={RotateCcw}
          onCancel={() => setModal(null)}
          onConfirm={() => confirmStatus(modal.doc, "ACTIVE")}
          title={t("reactivateConfirmTitle", { title: modal.doc.title })}
          tone="teal"
        />
      ) : null}

      {modal?.kind === "applyDrafts" ? (
        <StageApplyPrompt
          changes={modal.changes}
          onClose={() => setModal(null)}
          onDone={(message) => {
            setModal(null);
            showToast(message);
          }}
        />
      ) : null}

      {toastNode}
    </div>
  );
}
