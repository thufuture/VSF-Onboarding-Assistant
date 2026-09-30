"use client";

import {
  Archive,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  ChevronDown,
  Eye,
  FileText,
  Link2,
  ListChecks,
  Pencil,
  RotateCcw,
  Search,
  UploadCloud,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { chatApi } from "@/features/chat/api";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  DocumentCategoryResponseDTO,
  DocumentListItemResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { categoryStyle, type DocTone } from "./docCategory";
import styles from "./DocumentsListPage.module.scss";

const PAGE_SIZE = 6;
// Chiều cao tối thiểu của vùng bảng = đủ một trang đầy, để chân phân trang luôn nằm đáy thẻ.
const ROW_HEIGHT = 64;
const HEAD_HEIGHT = 41;

const API_ERROR_KEYS: Record<string, string> = {
  INGEST_FAILED: "errors.ingestFailed",
  CATEGORY_NOT_FOUND: "errors.categoryNotFound",
};

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) {
    const mapped = error.apiCode ? API_ERROR_KEYS[error.apiCode] : undefined;
    return t(mapped ?? `errors.${error.code}`);
  }
  return t("errors.unavailable");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN");
}

type Section = { id: string; level: number; heading: string | null; body: string };

// Cùng quy tắc tách section với backend (H1–H3 mở section mới) để mục lục khớp nội dung đã ingest.
function splitSections(markdown: string): Section[] {
  const sections: Section[] = [];
  let current: Section | null = null;
  for (const line of markdown.split("\n")) {
    const heading = /^(#{1,3})\s+(.+?)\s*$/.exec(line);
    if (heading) {
      current = { id: `sec-${sections.length}`, level: heading[1].length, heading: heading[2], body: "" };
      sections.push(current);
    } else {
      if (!current) {
        current = { id: `sec-${sections.length}`, level: 0, heading: null, body: "" };
        sections.push(current);
      }
      current.body += `${line}\n`;
    }
  }
  return sections.filter((s) => s.heading || s.body.trim());
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
  | { kind: "view"; doc: DocumentListItemResponseDTO }
  | { kind: "archive"; doc: DocumentListItemResponseDTO }
  | { kind: "reactivate"; doc: DocumentListItemResponseDTO };

/** "Tài liệu nguồn" thật — cổng bố cục và flow modal của prototype v15 (thêm / xem mục lục / sửa / phiên bản mới /
 * ngừng sử dụng có xác nhận / kích hoạt lại). "Xóa" của v15 được thay bằng chuyển trạng thái ARCHIVED để giữ lịch sử ingest. */
export function DocumentsListPage() {
  const t = useTranslations("portalDocuments");
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
  const [openFilter, setOpenFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const [file, setFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [docCategory, setDocCategory] = useState("");
  const [docVersion, setDocVersion] = useState("1.0");
  const [docEffectiveFrom, setDocEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));

  const [viewMarkdown, setViewMarkdown] = useState<string | null>(null);
  const [viewFailed, setViewFailed] = useState(false);
  // Mục lục kiểu ngăn điều hướng của Word: đứng yên, làm nổi mục đang đọc theo vị trí cuộn của trang.
  const canvasRef = useRef<HTMLDivElement>(null);
  const [activeSec, setActiveSec] = useState<string | null>(null);

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
        (!categoryFilter || d.category_name === categoryFilter),
    );
  }, [documents, query, statusFilter, categoryFilter, usageFilter]);

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
    setModal({ kind: "upload" });
  }

  function openNewVersion(doc: DocumentListItemResponseDTO) {
    setFile(null);
    setDocVersion("");
    setModal({ kind: "newVersion", doc });
  }

  function openEdit(doc: DocumentListItemResponseDTO) {
    setDocTitle(doc.title);
    setDocCategory(doc.category_slug);
    setModal({ kind: "edit", doc });
  }

  function openView(doc: DocumentListItemResponseDTO) {
    setViewMarkdown(null);
    setViewFailed(false);
    setActiveSec(null);
    setModal({ kind: "view", doc });
    if (doc.latest_version_id === null) {
      setViewFailed(true);
      return;
    }
    chatApi
      .getDocument(doc.latest_version_id)
      .then((result) => setViewMarkdown(result.markdown))
      .catch(() => setViewFailed(true));
  }

  async function submitUpload(event: FormEvent, existing?: DocumentListItemResponseDTO) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("title", existing?.title ?? docTitle);
      form.append("category_slug", existing?.category_slug ?? docCategory);
      // Cùng source_key = thêm phiên bản mới của tài liệu cũ; khác = tài liệu mới.
      form.append("source_key", existing?.source_key ?? `portal-${Date.now()}`);
      form.append("version_label", docVersion);
      form.append("effective_from", docEffectiveFrom);
      const result = await portalHrApi.uploadDocument(form);
      setModal(null);
      showToast(t("upload.success", { sections: result.section_count, chunks: result.chunk_count }));
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

  async function confirmStatus(doc: DocumentListItemResponseDTO, next: "ACTIVE" | "ARCHIVED") {
    setError(null);
    setBusy(true);
    try {
      await portalHrApi.setDocumentStatus(doc.id, { status: next });
      setModal(null);
      showToast(next === "ARCHIVED" ? t("notice.archived") : t("notice.reactivated"));
      reload();
    } catch (caught) {
      setError(errorMessage(t, caught));
      setModal(null);
    } finally {
      setBusy(false);
    }
  }

  const sections = viewMarkdown ? splitSections(viewMarkdown) : [];

  function scrollToSection(id: string) {
    const box = canvasRef.current;
    const el = document.getElementById(id);
    if (!box || !el) return;
    const top = el.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop - 18;
    box.scrollTo({ top, behavior: "smooth" });
    setActiveSec(id);
  }

  function syncActiveSection() {
    const box = canvasRef.current;
    if (!box) return;
    const boxTop = box.getBoundingClientRect().top;
    let current: string | null = null;
    for (const item of sections) {
      if (!item.heading) continue;
      const el = document.getElementById(item.id);
      if (el && el.getBoundingClientRect().top - boxTop <= 60) current = item.id;
    }
    setActiveSec(current);
  }

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

      <div className={styles.kpiGrid}>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.total")}</small>
            <span className={`${styles.ichip} ${styles.toneBlue}`}>
              <BookOpen aria-hidden="true" size={15} />
            </span>
          </div>
          <b>{total}</b>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.ready")}</small>
            <span className={`${styles.ichip} ${styles.toneTeal}`}>
              <CheckCircle2 aria-hidden="true" size={15} />
            </span>
          </div>
          <b>{readyCount}</b>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.pending")}</small>
            <span className={`${styles.ichip} ${styles.toneAmber}`}>
              <Clock aria-hidden="true" size={15} />
            </span>
          </div>
          <b>{pendingCount}</b>
        </div>
        <div className={styles.kpi}>
          <div className={styles.kh}>
            <small>{t("kpi.used")}</small>
            <span className={`${styles.ichip} ${styles.toneIndigo}`}>
              <ListChecks aria-hidden="true" size={15} />
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
            <thead>
              <tr>
                <th>{t("table.document")}</th>
                <th>{t("table.category")}</th>
                <th>{t("table.sections")}</th>
                <th>{t("table.status")}</th>
                <th>{t("table.tasks")}</th>
                <th>{t("table.updated")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {documents === null ? (
                <tr>
                  <td colSpan={7}>{t("loading")}</td>
                </tr>
              ) : pageItems.length === 0 ? (
                <tr>
                  <td colSpan={7}>{t("empty")}</td>
                </tr>
              ) : (
                pageItems.map((doc) => {
                  const cat = categoryStyle(doc.category_name);
                  return (
                    <tr className={doc.status !== "ACTIVE" ? styles.rowOff : ""} key={doc.id}>
                      <td>
                        <div className={styles.docName}>
                          <span className={`${styles.docIcon} ${styles[`tone_${cat.tone}`]}`}>
                            <FileText aria-hidden="true" size={16} />
                          </span>
                          <div>
                            <b>{doc.title}</b>
                            {doc.source_key ? <small>{doc.source_key}</small> : null}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`${styles.kind} ${styles[`tone_${cat.tone}`]}`}>
                          {cat.icon} {doc.category_name}
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
                        <span className={styles.status} data-status={doc.status}>
                          <i />
                          {t(`status.${doc.status}`)}
                        </span>
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
                          {doc.owner_name ? <small>{doc.owner_name}</small> : null}
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
                            <Eye aria-hidden="true" size={13} />
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
                <select id="up-cat" onChange={(e) => setDocCategory(e.target.value)} required value={docCategory}>
                  {categories.map((c) => (
                    <option key={c.slug} value={c.slug}>
                      {c.name}
                    </option>
                  ))}
                </select>
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
                  required
                  type="date"
                  value={docEffectiveFrom}
                />
              </div>
            </div>
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
                  required
                  type="date"
                  value={docEffectiveFrom}
                />
              </div>
            </div>
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
                <select id="ed-cat" onChange={(e) => setDocCategory(e.target.value)} value={docCategory}>
                  {categories.map((c) => (
                    <option key={c.slug} value={c.slug}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </form>
        </PortalModal>
      ) : null}

      {modal?.kind === "view" ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              {modal.doc.latest_version_id ? (
                <a
                  className={m.btnSec}
                  href={portalHrApi.originalDocumentUrl(modal.doc.latest_version_id)}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  <FileText aria-hidden="true" size={14} /> {t("viewOriginal")}
                </a>
              ) : null}
              <button className={m.btnSec} onClick={() => setModal(null)} type="button">
                {t("closeButton")}
              </button>
            </>
          }
          icon={FileText}
          onClose={() => setModal(null)}
          subtitle={`${modal.doc.category_name} · ${t("sectionCount", { count: modal.doc.section_count })}`}
          title={modal.doc.title}
          tone="indigo"
          vwide
        >
          {viewFailed ? (
            <p className={m.faint}>{t("viewFailed")}</p>
          ) : viewMarkdown === null ? (
            <p className={m.faint}>{t("loading")}</p>
          ) : (
            <div className={styles.docRead}>
              <nav aria-label={t("toc")} className={styles.docToc}>
                <b>{t("toc")}</b>
                <div className={styles.docTocList}>
                  {sections
                    .filter((s) => s.heading)
                    .map((s) => (
                      <button
                        className={`${styles[`lvl${s.level}`]} ${activeSec === s.id ? styles.tocOn : ""}`}
                        key={s.id}
                        onClick={() => scrollToSection(s.id)}
                        type="button"
                      >
                        {s.heading}
                      </button>
                    ))}
                </div>
              </nav>
              <div className={styles.docCanvas} onScroll={syncActiveSection} ref={canvasRef}>
                <article className={styles.docPage}>
                  {sections.map((s) => {
                    const Heading = (s.level <= 1 ? "h2" : s.level === 2 ? "h3" : "h4") as "h2" | "h3" | "h4";
                    return (
                      <section id={s.id} key={s.id}>
                        {s.heading ? <Heading className={styles[`hd${Math.max(s.level, 1)}`]}>{s.heading}</Heading> : null}
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{s.body}</ReactMarkdown>
                      </section>
                    );
                  })}
                </article>
              </div>
            </div>
          )}
        </PortalModal>
      ) : null}

      {modal?.kind === "archive" ? (
        <ConfirmModal
          body={t("archiveConfirmBody")}
          busy={busy}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={Archive}
          confirmLabel={t("archiveConfirmButton")}
          danger
          icon={Archive}
          onCancel={() => setModal(null)}
          onConfirm={() => confirmStatus(modal.doc, "ARCHIVED")}
          title={t("archiveConfirmTitle", { title: modal.doc.title })}
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

      {toastNode}
    </div>
  );
}
