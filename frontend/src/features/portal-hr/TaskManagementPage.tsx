"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Clock,
  Copy,
  Eye,
  Flag,
  Info,
  Link2,
  ListChecks,
  Pencil,
  Plus,
  Search,
  Send,
  Sparkles,
  Trash2,
  Workflow,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  TaskGroupDTO,
  TaskNodeResponseDTO,
  TemplateNodeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";
import { parseTaskBody, serializeTaskBody } from "@/features/portal-hr/taskBody";
import { Link } from "@/i18n/navigation";

import styles from "./TaskManagementPage.module.scss";

// Hình học roadmap: canvas cao 470, nút rải đều 7%→93%; độ cao lệch nhẹ (±17px) để đường cong mềm như sóng thoải,
// thẻ xen kẽ trên (top 16) / dưới (top 298), rộng 176 và cao 138 (dải màu đầu thẻ + thân + nút thao tác).
const CANVAS_H = 470;
const CARD_W = 196;
const CARD_H = 138;
const CARD_TOP = 16;
const CARD_BOTTOM = 298;
const CENTERS = [232, 210, 240, 214, 236, 208, 238, 216, 234, 212, 240, 218];
const SIZES = [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50];

// Nhóm task cố định (Hồ sơ / Đào tạo / Thiết bị / Văn phòng) — mỗi nhóm một màu dịu và một icon phẳng; chưa phân nhóm dùng xám.
const GROUPS: { key: TaskGroupDTO; cls: string; color: string; flat: FlatIconName; tone: FlatTone }[] = [
  { key: "PROFILE", cls: "catC1", color: "#1f8a5f", flat: "file", tone: "green" },
  { key: "TRAINING", cls: "catC2", color: "#1b6fb8", flat: "book", tone: "blue" },
  { key: "DEVICE", cls: "catC3", color: "#4457b3", flat: "laptop", tone: "indigo" },
  { key: "OFFICE", cls: "catC4", color: "#d18a12", flat: "building", tone: "amber" },
];
const NO_GROUP = { key: null, cls: "catC7", color: "#6b7a8c", flat: "tasks" as FlatIconName, tone: "slate" as FlatTone };

export const TASKS_CHANGED_EVENT = "portal-tasks-changed";
export const ADD_STAGE_EVENT = "portal-add-stage";

const API_ERROR_KEYS: Record<string, string> = {
  TEMPLATE_ALREADY_PUBLISHED: "errors.published",
  TEMPLATE_EMPTY: "errors.empty",
  DEPENDENCY_CYCLE: "errors.cycle",
  DEPENDENCY_SELF: "errors.cycle",
  STAGE_OUT_OF_TEMPLATE: "errors.stageOutOfTemplate",
};

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) {
    const mapped = error.apiCode ? API_ERROR_KEYS[error.apiCode] : undefined;
    return t(mapped ?? `errors.${error.code}`);
  }
  return t("errors.unavailable");
}

function notifyChanged() {
  window.dispatchEvent(new Event(TASKS_CHANGED_EVENT));
}

type TaskForm = {
  title: string;
  order: string;
  stageId: number;
  required: boolean;
  group: TaskGroupDTO | "";
  why: string;
  done: string;
  steps: string;
  depends: number[];
};

type TabKey = "info" | "guide" | "prereq" | "links";

/** "Quản lý lộ trình onboarding" — cổng đúng DOM/CSS của view h-tasks (v15): tiêu đề, 4 KPI, tìm kiếm,
 * roadmap sóng ngang thẻ xen kẽ, chú giải; mọi nút (thêm/sửa/xem/nhân bản/xóa/thêm ngày/xuất bản) mở modal như v15.
 * Dữ liệu thật từ GET /portal/journey-templates/mine. Menu "ngày" nằm ở sidebar (TasksSidebar), chọn qua ?stage=. */
export function TaskManagementPage() {
  const t = useTranslations("portalTasks");
  const params = useSearchParams();
  const stageParam = Number(params.get("stage"));
  const [toastNode, showToast] = useToast();

  const [templates, setTemplates] = useState<TemplateNodeResponseDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const [taskModal, setTaskModal] = useState<{ mode: "create" | "edit"; task?: TaskNodeResponseDTO } | null>(null);
  const [tab, setTab] = useState<TabKey>("info");
  const [form, setForm] = useState<TaskForm | null>(null);
  const [viewingTask, setViewingTask] = useState<TaskNodeResponseDTO | null>(null);
  const [deletingTask, setDeletingTask] = useState<TaskNodeResponseDTO | null>(null);
  const [duplicatingTask, setDuplicatingTask] = useState<TaskNodeResponseDTO | null>(null);
  const [publishing, setPublishing] = useState(false);

  const [showAddStage, setShowAddStage] = useState(false);
  const [stageNumber, setStageNumber] = useState("1");
  const [stageTitle, setStageTitle] = useState("");

  function reload() {
    portalHrApi
      .listMyTemplates()
      .then((result) => setTemplates(result))
      .catch((caught: unknown) => setError(errorMessage(t, caught)));
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allStages = useMemo(
    () =>
      (templates ?? []).flatMap((tpl) =>
        tpl.stages.map((s) => ({
          ...s,
          templateId: tpl.id,
          templateTitle: tpl.title,
          templateStatus: tpl.status,
        })),
      ),
    [templates],
  );
  const selectedStage = allStages.find((s) => s.id === stageParam) ?? allStages[0] ?? null;
  const selectedTemplate = (templates ?? []).find((tpl) => tpl.id === selectedStage?.templateId) ?? null;

  const totalTasks = allStages.reduce((sum, s) => sum + s.tasks.length, 0);
  const publishedTasks = allStages
    .filter((s) => s.templateStatus === "PUBLISHED")
    .reduce((sum, s) => sum + s.tasks.length, 0);
  const draftTasks = totalTasks - publishedTasks;
  const missingTasks = allStages.reduce((sum, s) => sum + s.tasks.filter((tk) => !tk.body_markdown.trim()).length, 0);

  const isPublished = selectedStage?.templateStatus === "PUBLISHED";
  const stageTasks = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (selectedStage?.tasks ?? []).filter((tk) => !q || tk.title.toLowerCase().includes(q));
  }, [selectedStage, query]);

  const count = stageTasks.length;
  // Task cùng lộ trình (để chọn tiên quyết) và các giai đoạn cùng lộ trình (để chọn "Ngày").
  const templateStages = selectedTemplate?.stages ?? [];
  // Điểm 0 = "Bắt đầu", điểm 1..n = task, điểm n+1 = "Kết thúc": cả ba loại đều là nút nằm trên đường.
  const total = count + 2;
  const layout = Array.from({ length: total }, (_, j) => {
    const x = 6 + (j * 88) / (total - 1);
    const size = SIZES[j % SIZES.length];
    const center = CENTERS[j % CENTERS.length];
    return { x, size, center, top: center - size / 2, onTop: (j - 1) % 2 === 0 };
  });
  // Đường cong Catmull-Rom qua mọi điểm (toạ độ viewBox 1000 = phần trăm × 10).
  const pts = layout.map((p) => ({ x: p.x * 10, y: p.center }));
  const path = pts
    .map((q, i) => {
      if (i === 0) return `M ${q.x} ${q.y}`;
      const p0 = pts[i - 2] ?? pts[i - 1];
      const p1 = pts[i - 1];
      const p3 = pts[i + 1] ?? q;
      const c1x = p1.x + (q.x - p0.x) / 6;
      const c1y = p1.y + (q.y - p0.y) / 6;
      const c2x = q.x - (p3.x - p1.x) / 6;
      const c2y = q.y - (p3.y - p1.y) / 6;
      return `C ${c1x} ${c1y}, ${c2x} ${c2y}, ${q.x} ${q.y}`;
    })
    .join(" ");

  const toneOf = (group: TaskGroupDTO | null) => GROUPS.find((g) => g.key === group) ?? NO_GROUP;

  const templateTasks = templateStages.flatMap((s) => s.tasks.map((tk) => ({ ...tk, stageTitle: s.title })));

  function openCreate() {
    if (!selectedStage) return;
    setTab("info");
    setForm({
      title: "",
      order: String(selectedStage.tasks.length + 1),
      stageId: selectedStage.id,
      required: true,
      group: "",
      why: "",
      done: "",
      steps: "",
      depends: [],
    });
    setTaskModal({ mode: "create" });
  }

  function openEdit(task: TaskNodeResponseDTO) {
    const parts = parseTaskBody(task.body_markdown);
    setTab("info");
    setForm({
      title: task.title,
      order: String(task.sort_order),
      stageId: task.journey_stage_id,
      required: task.required,
      group: task.task_group ?? "",
      why: parts.why,
      done: parts.done,
      steps: parts.steps.join("\n"),
      depends: task.depends_on,
    });
    setTaskModal({ mode: "edit", task });
  }

  function openAddStage() {
    setStageNumber(String((allStages.length || 0) + 1));
    setStageTitle("");
    setShowAddStage(true);
  }

  const stageCount = allStages.length;
  useEffect(() => {
    // Nút "Thêm ngày hoặc giai đoạn" ở sidebar báo qua sự kiện; số ngày gợi ý = số giai đoạn hiện có + 1.
    const onAddStage = () => {
      setStageNumber(String(stageCount + 1));
      setStageTitle("");
      setShowAddStage(true);
    };
    window.addEventListener(ADD_STAGE_EVENT, onAddStage);
    return () => window.removeEventListener(ADD_STAGE_EVENT, onAddStage);
  }, [stageCount]);

  function patchForm(patch: Partial<TaskForm>) {
    setForm((current) => (current ? { ...current, ...patch } : current));
  }

  async function handleSaveTask(event: FormEvent) {
    event.preventDefault();
    if (!form || !taskModal) return;
    setError(null);
    setBusy("task");
    const body = serializeTaskBody(
      { why: form.why, done: form.done, steps: form.steps.split("\n") },
      form.title,
    );
    const order = Number.parseInt(form.order, 10);
    try {
      if (taskModal.mode === "create") {
        await portalHrApi.createTaskManual(form.stageId, {
          title: form.title,
          body_markdown: body,
          required: form.required,
          task_group: form.group || null,
          sort_order: Number.isNaN(order) ? null : order,
          depends_on: form.depends,
        });
        showToast(t("notice.created"));
      } else if (taskModal.task) {
        await portalHrApi.updateTaskTemplate(taskModal.task.id, {
          title: form.title,
          body_markdown: body,
          required: form.required,
          task_group: form.group || null,
          journey_stage_id: form.stageId,
          sort_order: Number.isNaN(order) ? null : order,
          depends_on: form.depends,
        });
        showToast(t("notice.updated"));
      }
      setTaskModal(null);
      reload();
      notifyChanged();
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleAddStage(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy("stage");
    try {
      const draft = (templates ?? []).find((tpl) => tpl.status === "DRAFT");
      const templateId =
        draft?.id ??
        (
          await portalHrApi.createJourneyTemplate({
            code: "tpl-" + Date.now().toString(36),
            title: t("defaultTemplateTitle"),
          })
        ).id;
      const order = Number.parseInt(stageNumber, 10);
      await portalHrApi.createJourneyStage(templateId, {
        title: stageTitle,
        sort_order: Number.isNaN(order) ? (draft?.stages.length ?? 0) + 1 : order,
      });
      setShowAddStage(false);
      showToast(t("notice.stageCreated"));
      reload();
      notifyChanged();
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleConfirmDuplicate() {
    if (!duplicatingTask) return;
    setError(null);
    setBusy("dup");
    try {
      await portalHrApi.createTaskManual(duplicatingTask.journey_stage_id, {
        title: `${duplicatingTask.title} ${t("copySuffix")}`,
        body_markdown: duplicatingTask.body_markdown,
        required: duplicatingTask.required,
        task_group: duplicatingTask.task_group,
        sort_order: duplicatingTask.sort_order + 1,
        depends_on: duplicatingTask.depends_on,
      });
      setDuplicatingTask(null);
      showToast(t("notice.duplicated"));
      reload();
      notifyChanged();
    } catch (caught) {
      setDuplicatingTask(null);
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleConfirmDelete() {
    if (!deletingTask) return;
    setError(null);
    setBusy("delete");
    try {
      await portalHrApi.deleteTaskTemplate(deletingTask.id);
      setDeletingTask(null);
      showToast(t("notice.deleted"));
      reload();
      notifyChanged();
    } catch (caught) {
      setDeletingTask(null);
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleConfirmPublish() {
    if (!selectedTemplate) return;
    setError(null);
    setBusy("publish");
    try {
      await portalHrApi.publishTemplate(selectedTemplate.id);
      setPublishing(false);
      showToast(t("notice.published"));
      reload();
      notifyChanged();
    } catch (caught) {
      setPublishing(false);
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  const tabs: { key: TabKey; icon: typeof Info; label: string }[] = [
    { key: "info", icon: Info, label: t("tabs.info") },
    { key: "guide", icon: ClipboardList, label: t("tabs.guide") },
    { key: "prereq", icon: Workflow, label: t("tabs.prereq") },
    { key: "links", icon: Link2, label: t("tabs.links") },
  ];

  const viewParts = viewingTask ? parseTaskBody(viewingTask.body_markdown) : null;
  const viewStage = viewingTask ? allStages.find((s) => s.id === viewingTask.journey_stage_id) : null;

  return (
    <div className={styles.page}>
      <div className={styles.entTitle}>
        <div className={styles.entTitleCopy}>
          <span className={styles.entTitleIcon}>
            <ListChecks aria-hidden="true" size={22} />
          </span>
          <div>
            <h1>{t("title")}</h1>
            <p>{t("description")}</p>
          </div>
        </div>
        <div className={styles.row}>
          <Link className={styles.btnSec} href="/admin/ai-tasks">
            <Sparkles aria-hidden="true" size={14} /> {t("createWithAi")}
          </Link>
          <button className={styles.btnSec} onClick={openAddStage} type="button">
            <Plus aria-hidden="true" size={14} /> {t("addStageShort")}
          </button>
          {selectedTemplate && !isPublished ? (
            <button className={styles.btnSec} onClick={() => setPublishing(true)} type="button">
              <Send aria-hidden="true" size={14} /> {t("publish")}
            </button>
          ) : null}
          <button className={styles.btn} disabled={!selectedStage || isPublished} onClick={openCreate} type="button">
            <Plus aria-hidden="true" size={14} /> {t("addTask")}
          </button>
        </div>
      </div>

      {error ? <p className={styles.banner + " " + styles.bannerError}>{error}</p> : null}

      <div className={styles.kpis}>
        <div className={styles.kpi}>
          <span className={styles.kpiBlue}>
            <ListChecks aria-hidden="true" size={18} />
          </span>
          <div>
            <small>{t("kpi.total")}</small>
            <b>{totalTasks}</b>
            <p>{t("kpi.totalSub")}</p>
          </div>
        </div>
        <div className={styles.kpi}>
          <span className={styles.kpiAmber}>
            <Pencil aria-hidden="true" size={18} />
          </span>
          <div>
            <small>{t("kpi.draft")}</small>
            <b>{draftTasks}</b>
            <p>{t("kpi.draftSub")}</p>
          </div>
        </div>
        <div className={styles.kpi}>
          <span className={styles.kpiTeal}>
            <CheckCircle2 aria-hidden="true" size={18} />
          </span>
          <div>
            <small>{t("kpi.published")}</small>
            <b>{publishedTasks}</b>
            <p>{t("kpi.publishedSub")}</p>
          </div>
        </div>
        <div className={styles.kpi}>
          <span className={styles.kpiRose}>
            <AlertTriangle aria-hidden="true" size={18} />
          </span>
          <div>
            <small>{t("kpi.missing")}</small>
            <b>{missingTasks}</b>
            <p>{t("kpi.missingSub")}</p>
          </div>
        </div>
      </div>

      <div className={styles.toolbar}>
        <div className={styles.search}>
          <Search aria-hidden="true" size={14} />
          <input
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("searchPlaceholder", { stage: selectedStage?.title ?? "" })}
            value={query}
          />
        </div>
      </div>

      {selectedStage ? (
        <section className={styles.journey}>
          <div className={styles.journeyHead}>
            <div className={styles.journeyTitle}>
              <div>
                <h2>{selectedStage.title}</h2>
                <small>
                  {selectedStage.templateTitle} · {t("taskCount", { count: selectedStage.tasks.length })}
                </small>
              </div>
            </div>
            <button className={styles.btnSecSm} disabled={isPublished} onClick={openCreate} type="button">
              <Plus aria-hidden="true" size={13} /> {t("addTask")}
            </button>
          </div>

          {stageTasks.length === 0 ? (
            <div className={styles.emptyRoad}>
              <Flag aria-hidden="true" size={28} />
              <b>{t("emptyTitle")}</b>
              <span>{t("emptyTasks")}</span>
            </div>
          ) : (
            <div className={styles.roadScroll}>
              <div className={styles.canvas} style={{ height: CANVAS_H, minWidth: Math.max(820, count * 124) }}>
                <svg
                  aria-hidden="true"
                  className={styles.roadSvg}
                  preserveAspectRatio="none"
                  viewBox={`0 0 1000 ${CANVAS_H}`}
                >
                  <path className={styles.roadBed} d={path} vectorEffect="non-scaling-stroke" />
                  <path className={styles.roadLine} d={path} vectorEffect="non-scaling-stroke" />
                  <path className={styles.roadDash} d={path} vectorEffect="non-scaling-stroke" />
                </svg>

                {[
                  { p: layout[0], kind: "start", flat: "flag" as FlatIconName, tone: "green" as FlatTone, label: t("start") },
                  { p: layout[total - 1], kind: "finish", flat: "award" as FlatIconName, tone: "amber" as FlatTone, label: t("finish") },
                ].map((end) => (
                  <div className={`${styles.endNode} ${styles[`end_${end.kind}`]}`} key={end.kind}>
                    <span
                      className={styles.endCircle}
                      style={{ left: `calc(${end.p.x}% - 24px)`, top: end.p.center - 24 }}
                    >
                      <FlatIcon name={end.flat} size={24} tone={end.tone} />
                    </span>
                    <em style={{ left: `calc(${end.p.x}% - 40px)`, top: end.p.center + 30 }}>{end.label}</em>
                  </div>
                ))}

                {stageTasks.map((task, i) => {
                  const p = layout[i + 1];
                  const tone = toneOf(task.task_group);
                  const tetherTop = p.onTop ? CARD_TOP + CARD_H : p.top + p.size;
                  const tetherHeight = p.onTop ? p.top - (CARD_TOP + CARD_H) : CARD_BOTTOM - (p.top + p.size);
                  return (
                    <article className={`${styles.roadItem} ${styles[tone.cls]}`} key={task.id}>
                      <i className={`${styles.tether} ${p.onTop ? styles.tetherTop : styles.tetherBottom}`} style={{ left: `${p.x}%`, top: tetherTop, height: Math.max(tetherHeight, 0) }} />
                      <button
                        aria-label={task.title}
                        className={styles.node}
                        onClick={() => setViewingTask(task)}
                        style={{ left: `calc(${p.x}% - ${p.size / 2}px)`, top: p.top, width: p.size, height: p.size }}
                        type="button"
                      >
                        <FlatIcon name={tone.flat} size={24} tone={tone.tone} />
                        <i className={styles.nodeNum}>{i + 1}</i>
                      </button>
                      <div
                        className={styles.card}
                        style={{
                          width: CARD_W,
                          left: `clamp(4px, calc(${p.x}% - ${CARD_W / 2}px), calc(100% - ${CARD_W + 4}px))`,
                          top: p.onTop ? CARD_TOP : CARD_BOTTOM,
                        }}
                      >
                        <div className={styles.cardBand}>
                          <small>
                            {t("taskNo", { n: String(i + 1).padStart(2, "0") })}
                          </small>
                          <span className={styles.bandPill}>{isPublished ? t("statusPublished") : t("statusDraft")}</span>
                        </div>
                        <div className={styles.cardBody}>
                          <h3 title={task.title}>{task.title}</h3>
                          <div className={styles.chips}>
                            <span>
                              <Clock aria-hidden="true" size={10} /> {task.required ? t("required") : t("optional")}
                            </span>
                            <span>
                              <ListChecks aria-hidden="true" size={10} /> {t("prereq", { count: task.depends_on.length })}
                            </span>
                          </div>
                        </div>
                        <div className={styles.actions}>
                          <button onClick={() => setViewingTask(task)} title={t("viewTask")} type="button">
                            <Eye aria-hidden="true" size={12} />
                          </button>
                          <button disabled={isPublished} onClick={() => openEdit(task)} title={t("edit")} type="button">
                            <Pencil aria-hidden="true" size={12} />
                          </button>
                          <button
                            disabled={isPublished}
                            onClick={() => setDuplicatingTask(task)}
                            title={t("duplicate")}
                            type="button"
                          >
                            <Copy aria-hidden="true" size={12} />
                          </button>
                          <button
                            className={styles.danger}
                            disabled={isPublished}
                            onClick={() => setDeletingTask(task)}
                            title={t("delete")}
                            type="button"
                          >
                            <Trash2 aria-hidden="true" size={12} />
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          )}

          <div className={styles.legend}>
            <b>{t("legend.title")}</b>
            {GROUPS.map((g) => (
              <span key={g.key}>
                <i style={{ background: g.color }} />
                {t(`group.${g.key}`)}
              </span>
            ))}
            {stageTasks.some((tk) => !tk.task_group) ? (
              <span>
                <i style={{ background: NO_GROUP.color }} />
                {t("group.none")}
              </span>
            ) : null}
            {isPublished ? <span className={styles.legendNote}>{t("publishedReadonly")}</span> : null}
          </div>
        </section>
      ) : templates === null ? (
        <p className={styles.faint}>{t("loading")}</p>
      ) : (
        <div className={styles.journey}>
          <div className={styles.emptyRoad}>
            <Flag aria-hidden="true" size={28} />
            <b>{t("noStagesTitle")}</b>
            <span>{t("noStages")}</span>
            <button className={styles.btn} onClick={openAddStage} type="button">
              <Plus aria-hidden="true" size={14} /> {t("addStage")}
            </button>
          </div>
        </div>
      )}

      {taskModal && form ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setTaskModal(null)} type="button">
                {t("cancel")}
              </button>
              <button className={m.btn} disabled={busy === "task"} form="task-form" type="submit">
                <CheckCircle2 aria-hidden="true" size={14} /> {t("form.saveDraft")}
              </button>
            </>
          }
          icon={Pencil}
          onClose={() => setTaskModal(null)}
          tabs={tabs.map(({ key, icon: Icon, label }) => (
            <button
              className={`${m.mtab} ${tab === key ? m.mtabOn : ""}`}
              key={key}
              onClick={() => setTab(key)}
              type="button"
            >
              <Icon aria-hidden="true" size={14} />
              {label}
            </button>
          ))}
          title={taskModal.mode === "create" ? t("addTask") : t("editTitle")}
          wide
        >
          <form id="task-form" onSubmit={handleSaveTask}>
            <div className={m.fgrid} hidden={tab !== "info"}>
              <div className={m.span2}>
                <label htmlFor="tk-title">{t("form.title")}</label>
                <input
                  id="tk-title"
                  onChange={(e) => patchForm({ title: e.target.value })}
                  required
                  type="text"
                  value={form.title}
                />
              </div>
              <div>
                <label htmlFor="tk-order">{t("form.order", { max: (selectedStage?.tasks.length ?? 0) + (taskModal.mode === "create" ? 1 : 0) })}</label>
                <input
                  id="tk-order"
                  inputMode="numeric"
                  onChange={(e) => patchForm({ order: e.target.value })}
                  type="text"
                  value={form.order}
                />
              </div>
              <div>
                <label htmlFor="tk-stage">{t("form.day")}</label>
                <select id="tk-stage" onChange={(e) => patchForm({ stageId: Number(e.target.value) })} value={form.stageId}>
                  {templateStages.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="tk-comp">{t("form.completion")}</label>
                <select disabled id="tk-comp" value="SELF_CONFIRM">
                  <option value="SELF_CONFIRM">{t("form.selfConfirm")}</option>
                </select>
              </div>
              <div>
                <label htmlFor="tk-group">{t("form.group")}</label>
                <select
                  id="tk-group"
                  onChange={(e) => patchForm({ group: e.target.value as TaskGroupDTO | "" })}
                  value={form.group}
                >
                  <option value="">{t("group.none")}</option>
                  {GROUPS.map((g) => (
                    <option key={g.key} value={g.key}>
                      {t(`group.${g.key}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={m.subitem} style={{ marginTop: 22 }}>
                  <input
                    checked={form.required}
                    onChange={(e) => patchForm({ required: e.target.checked })}
                    type="checkbox"
                  />
                  <span>{t("form.requiredLong")}</span>
                </label>
              </div>
            </div>

            <div className={m.fgrid} hidden={tab !== "guide"}>
              <div className={m.span2}>
                <label htmlFor="tk-why">{t("form.why")}</label>
                <textarea id="tk-why" onChange={(e) => patchForm({ why: e.target.value })} value={form.why} />
              </div>
              <div className={m.span2}>
                <label htmlFor="tk-done">{t("form.done")}</label>
                <textarea id="tk-done" onChange={(e) => patchForm({ done: e.target.value })} value={form.done} />
              </div>
              <div className={m.span2}>
                <label htmlFor="tk-steps">{t("form.steps")}</label>
                <textarea
                  id="tk-steps"
                  onChange={(e) => patchForm({ steps: e.target.value })}
                  style={{ minHeight: 140 }}
                  value={form.steps}
                />
              </div>
            </div>

            <div hidden={tab !== "prereq"}>
              <p className={m.faint}>{t("form.prereqHint")}</p>
              <div className={m.chkList}>
                {templateTasks
                  .filter((tk) => tk.id !== taskModal.task?.id)
                  .map((tk) => (
                    <label className={m.subitem} key={tk.id}>
                      <input
                        checked={form.depends.includes(tk.id)}
                        onChange={(e) =>
                          patchForm({
                            depends: e.target.checked ? [...form.depends, tk.id] : form.depends.filter((id) => id !== tk.id),
                          })
                        }
                        type="checkbox"
                      />
                      <span>{tk.title}</span>
                    </label>
                  ))}
              </div>
            </div>

            <div hidden={tab !== "links"}>
              <div className={m.emptyPanel}>
                <Link2 aria-hidden="true" size={22} />
                <b>{t("form.linksTitle")}</b>
                <span>{t("form.linksSoon")}</span>
              </div>
            </div>
          </form>
        </PortalModal>
      ) : null}

      {viewingTask && viewParts ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <button className={m.btnSec} onClick={() => setViewingTask(null)} type="button">
              {t("closeButton")}
            </button>
          }
          icon={ListChecks}
          onClose={() => setViewingTask(null)}
          subtitle={`${viewStage?.title ?? ""} · ${t("form.selfConfirm")} · ${viewingTask.required ? t("required") : t("optional")}`}
          title={viewingTask.title}
          wide
        >
          <div className={styles.viewSummary}>
            <div>
              <small>{t("view.stage")}</small>
              <b>{viewStage?.title ?? "—"}</b>
            </div>
            <div>
              <small>{t("view.completion")}</small>
              <b>{t("form.selfConfirm")}</b>
            </div>
            <div>
              <small>{t("view.kind")}</small>
              <b>{viewingTask.required ? t("required") : t("optional")}</b>
            </div>
            <div>
              <small>{t("view.prereq")}</small>
              <b>
                {viewingTask.depends_on.length === 0
                  ? t("view.none")
                  : viewingTask.depends_on
                      .map((id) => templateTasks.find((tk) => tk.id === id)?.title ?? `#${id}`)
                      .join(", ")}
              </b>
            </div>
          </div>
          {viewParts.why ? (
            <section className={styles.viewSection}>
              <h3>
                <Info aria-hidden="true" size={14} /> {t("form.why")}
              </h3>
              <p>{viewParts.why}</p>
            </section>
          ) : null}
          {viewParts.done ? (
            <section className={styles.viewSection}>
              <h3>
                <CheckCircle2 aria-hidden="true" size={14} /> {t("form.done")}
              </h3>
              <p>{viewParts.done}</p>
            </section>
          ) : null}
          {viewParts.steps.length > 0 ? (
            <section className={styles.viewSection}>
              <h3>
                <ListChecks aria-hidden="true" size={14} /> {t("view.steps")}
              </h3>
              <ol>
                {viewParts.steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </section>
          ) : null}
        </PortalModal>
      ) : null}

      {deletingTask ? (
        <ConfirmModal
          body={t("deleteConfirmBody")}
          busy={busy === "delete"}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={Trash2}
          confirmLabel={t("deleteConfirmButton")}
          danger
          icon={Trash2}
          onCancel={() => setDeletingTask(null)}
          onConfirm={handleConfirmDelete}
          title={t("deleteConfirmTitle", { title: deletingTask.title })}
        />
      ) : null}

      {duplicatingTask ? (
        <ConfirmModal
          body={t("duplicateConfirmBody")}
          busy={busy === "dup"}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={Copy}
          confirmLabel={t("duplicateConfirmButton")}
          icon={Copy}
          onCancel={() => setDuplicatingTask(null)}
          onConfirm={handleConfirmDuplicate}
          title={t("duplicateConfirmTitle", { title: duplicatingTask.title })}
          tone="blue"
        />
      ) : null}

      {publishing && selectedTemplate ? (
        <ConfirmModal
          body={t("publishConfirmBody")}
          busy={busy === "publish"}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={Send}
          confirmLabel={t("publishConfirmButton")}
          icon={Send}
          onCancel={() => setPublishing(false)}
          onConfirm={handleConfirmPublish}
          title={t("publishConfirmTitle", { title: selectedTemplate.title })}
          tone="teal"
        />
      ) : null}

      {showAddStage ? (
        <PortalModal
          closeLabel={t("close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setShowAddStage(false)} type="button">
                {t("cancel")}
              </button>
              <button className={m.btn} disabled={busy === "stage"} form="stage-form" type="submit">
                <Plus aria-hidden="true" size={14} /> {t("form.createStage")}
              </button>
            </>
          }
          icon={Info}
          onClose={() => setShowAddStage(false)}
          title={t("addStage")}
        >
          <form id="stage-form" onSubmit={handleAddStage}>
            <p className={m.faint}>{t("form.stageHint")}</p>
            <div className={m.fgrid}>
              <div>
                <label htmlFor="st-num">{t("form.stageNumber")}</label>
                <input
                  id="st-num"
                  inputMode="numeric"
                  onChange={(e) => {
                    setStageNumber(e.target.value);
                    if (!stageTitle || /^Ngày \d+$/.test(stageTitle)) setStageTitle(`${t("form.dayWord")} ${e.target.value}`);
                  }}
                  type="text"
                  value={stageNumber}
                />
              </div>
              <div>
                <label htmlFor="st-title">{t("form.stageTitle")}</label>
                <input
                  id="st-title"
                  onChange={(e) => setStageTitle(e.target.value)}
                  placeholder={`${t("form.dayWord")} ${stageNumber}`}
                  required
                  type="text"
                  value={stageTitle}
                />
              </div>
            </div>
          </form>
        </PortalModal>
      ) : null}

      {toastNode}
    </div>
  );
}
