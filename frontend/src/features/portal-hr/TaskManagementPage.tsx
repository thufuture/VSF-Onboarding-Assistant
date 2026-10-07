"use client";

import {
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Clock,
  Copy,
  Eye,
  Flag,
  GitBranchPlus,
  Info,
  ListChecks,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  Workflow,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { ConfirmModal, modalStyles as m, PortalModal, useToast } from "@/components/portal-modal/PortalModal";
import { JourneyRoad, type RoadItem } from "@/components/roadmap/JourneyRoad";
import { TaskSources } from "@/components/task-sources/TaskSources";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  ApplyPreviewResponseDTO,
  TaskGroupDTO,
  TaskNodeResponseDTO,
  TemplateNodeResponseDTO,
  VersionNodeResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";
import { parseTaskBody, serializeTaskBody } from "@/features/portal-hr/taskBody";
import { Link } from "@/i18n/navigation";

import { RolloutModal } from "./RolloutModal";
import { StageVersionBar } from "./StageVersionBar";
import styles from "./TaskManagementPage.module.scss";

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
  VERSION_NOT_EDITABLE: "errors.versionNotEditable",
  VERSION_NOT_DRAFT: "errors.versionNotEditable",
  VERSION_EMPTY: "errors.versionEmpty",
  LAST_VERSION: "errors.lastVersion",
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

type TabKey = "info" | "guide" | "prereq";

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

  const [taskModal, setTaskModal] = useState<{ mode: "create" | "edit"; task?: TaskNodeResponseDTO } | null>(null);
  const [tab, setTab] = useState<TabKey>("info");
  const [form, setForm] = useState<TaskForm | null>(null);
  const [viewingTask, setViewingTask] = useState<TaskNodeResponseDTO | null>(null);
  const [deletingTask, setDeletingTask] = useState<TaskNodeResponseDTO | null>(null);
  const [duplicatingTask, setDuplicatingTask] = useState<TaskNodeResponseDTO | null>(null);
  const [pickedVersionId, setPickedVersionId] = useState<number | null>(null);
  const [applying, setApplying] = useState<{ version: VersionNodeResponseDTO; preview: ApplyPreviewResponseDTO | null } | null>(null);
  const [deletingVersion, setDeletingVersion] = useState<VersionNodeResponseDTO | null>(null);
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [rolloutVersion, setRolloutVersion] = useState<VersionNodeResponseDTO | null>(null);

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

  // Phiên bản đang xem của ngày: bản vừa bấm (nếu thuộc ngày này), không thì bản mặc định (đang áp dụng, không có thì nháp).
  const stageVersions = useMemo(() => selectedStage?.versions ?? [], [selectedStage]);
  const selectedVersion =
    stageVersions.find((v) => v.id === pickedVersionId) ??
    stageVersions.find((v) => v.id === selectedStage?.default_version_id) ??
    stageVersions[0] ??
    null;
  // Bản nháp mới nhất của ngày (nếu có): nhân viên CHƯA thấy gì cho tới khi HR bấm "Cập nhật cho nhân viên".
  const pendingDraft = [...stageVersions].filter((v) => v.status === "DRAFT").sort((a, b) => b.version_no - a.version_no)[0] ?? null;
  // Chỉ bản nháp sửa được; bản đang áp dụng và lưu trữ chỉ xem (sửa nhầm sẽ đổi lộ trình mà không ai biết).
  const readOnly = selectedVersion?.status !== "DRAFT";

  // Thống kê chỉ tính cho phiên bản đang xem.
  const stageTasks = useMemo(() => selectedVersion?.tasks ?? [], [selectedVersion]);
  const totalTasks = stageTasks.length;
  const appliedTasks = selectedVersion?.status === "APPLIED" ? totalTasks : 0;
  const draftTasks = selectedVersion?.status === "DRAFT" ? totalTasks : 0;
  const missingTasks = stageTasks.filter((tk) => !tk.body_markdown.trim()).length;

  // Task cùng lộ trình (để chọn tiên quyết) và các giai đoạn cùng lộ trình (để chọn "Ngày").
  const templateStages = selectedTemplate?.stages ?? [];
  const roadItems: RoadItem[] = stageTasks.map((task) => ({
    id: task.id,
    title: task.title,
    group: task.task_group,
    pill: selectedVersion ? t(`versions.status.${selectedVersion.status}`) : "",
    chips: [
      { icon: <Clock aria-hidden="true" size={10} />, label: task.required ? t("required") : t("optional") },
      { icon: <ListChecks aria-hidden="true" size={10} />, label: t("prereq", { count: task.depends_on.length }) },
    ],
  }));

  // Tiên quyết chỉ chọn được trong CÙNG phiên bản (Q2).
  const templateTasks = stageTasks.map((tk) => ({ ...tk, stageTitle: selectedStage?.title ?? "" }));

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
        const payload = {
          title: form.title,
          body_markdown: body,
          required: form.required,
          task_group: form.group || null,
          sort_order: Number.isNaN(order) ? null : order,
          depends_on: form.depends,
        };
        // Thêm vào đúng bản nháp đang xem; chọn ngày khác thì vào bản nháp làm việc của ngày đó.
        if (selectedVersion && form.stageId === selectedStage?.id) {
          await portalHrApi.createTaskInVersion(selectedVersion.id, payload);
        } else {
          await portalHrApi.createTaskManual(form.stageId, payload);
        }
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
      const draft = (templates ?? [])[0];
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

  async function handleCreateDraft() {
    if (!selectedStage || !selectedVersion) return;
    setError(null);
    setBusy("version");
    try {
      const created = await portalHrApi.createStageVersion(selectedStage.id, { from_version_id: selectedVersion.id });
      setCreatingDraft(false);
      setPickedVersionId(created.id);
      showToast(t("notice.draftCreated", { n: created.version_no }));
      reload();
      notifyChanged();
    } catch (caught) {
      setCreatingDraft(false);
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function openApply(version: VersionNodeResponseDTO) {
    setError(null);
    setApplying({ version, preview: null });
    try {
      const preview = await portalHrApi.previewApplyVersion(version.id);
      setApplying({ version, preview });
    } catch (caught) {
      setApplying(null);
      setError(errorMessage(t, caught));
    }
  }

  async function handleConfirmApply() {
    if (!applying) return;
    setError(null);
    setBusy("apply");
    try {
      const result = await portalHrApi.applyStageVersion(applying.version.id);
      setApplying(null);
      showToast(t("notice.applied", { n: result.version.version_no, count: result.notified_count }));
      reload();
      notifyChanged();
    } catch (caught) {
      setApplying(null);
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleConfirmDeleteVersion() {
    if (!deletingVersion) return;
    setError(null);
    setBusy("deleteVersion");
    try {
      await portalHrApi.deleteStageVersion(deletingVersion.id);
      setDeletingVersion(null);
      setPickedVersionId(null);
      showToast(t("notice.draftDeleted"));
      reload();
      notifyChanged();
    } catch (caught) {
      setDeletingVersion(null);
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  const tabs: { key: TabKey; icon: typeof Info; label: string }[] = [
    { key: "info", icon: Info, label: t("tabs.info") },
    { key: "guide", icon: ClipboardList, label: t("tabs.guide") },
    { key: "prereq", icon: Workflow, label: t("tabs.prereq") },
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
          <button className={styles.btn} disabled={!selectedStage || readOnly} onClick={openCreate} type="button">
            <Plus aria-hidden="true" size={14} /> {t("addTask")}
          </button>
        </div>
      </div>

      {error ? <p className={styles.banner + " " + styles.bannerError}>{error}</p> : null}

      {pendingDraft ? (
        <div className={styles.banner + " " + styles.bannerWarn} data-testid="draft-banner">
          <span>{t("draftBanner.text", { day: selectedStage?.title ?? "", n: pendingDraft.version_no })}</span>
          <span className={styles.bannerActions}>
            {pendingDraft.id !== selectedVersion?.id ? (
              <button className={styles.btnSec} onClick={() => setPickedVersionId(pendingDraft.id)} type="button">
                {t("draftBanner.view")}
              </button>
            ) : null}
            <button className={styles.btn} disabled={busy !== null} onClick={() => void openApply(pendingDraft)} type="button">
              <CheckCircle2 aria-hidden="true" size={14} /> {t("draftBanner.apply")}
            </button>
          </span>
        </div>
      ) : null}

      {selectedStage ? (
        <section className={styles.journey}>
          <div className={styles.journeyHead}>
            <div className={styles.journeyTitle}>
              <span className={styles.journeyIcon}>
                <FlatIcon name="route" size={26} tone="blue" />
              </span>
              <div>
                <h2>{selectedStage.title}</h2>
                <small>
                  {selectedStage.templateTitle} · {t("taskCount", { count: stageTasks.length })}
                </small>
                <StageVersionBar
                  busy={busy !== null}
                  onApply={(version) => void openApply(version)}
                  onCreateDraft={() => setCreatingDraft(true)}
                  onDelete={setDeletingVersion}
                  onRollout={setRolloutVersion}
                  onSelect={setPickedVersionId}
                  selectedId={selectedVersion?.id ?? null}
                  versions={stageVersions}
                />
              </div>
            </div>
            <div className={styles.journeyRight}>
            <dl className={styles.journeyStats}>
              <div>
                <FlatIcon name="tasks" size={24} tone="blue" />
                <dt>{t("kpi.total")}</dt>
                <dd>{totalTasks}</dd>
              </div>
              <div>
                <FlatIcon name="file" size={24} tone="amber" />
                <dt>{t("kpi.draft")}</dt>
                <dd>{draftTasks}</dd>
              </div>
              <div>
                <FlatIcon name="check" size={24} tone="green" />
                <dt>{t("kpi.applied")}</dt>
                <dd>{appliedTasks}</dd>
              </div>
              <div>
                <FlatIcon name="alert" size={24} tone="rose" />
                <dt>{t("kpi.missing")}</dt>
                <dd>{missingTasks}</dd>
              </div>
            </dl>
            <button className={styles.btnSecSm} disabled={readOnly} onClick={openCreate} type="button">
              <Plus aria-hidden="true" size={13} /> {t("addTask")}
            </button>
            </div>
          </div>

          {stageTasks.length === 0 ? (
            <div className={styles.emptyRoad}>
              <Flag aria-hidden="true" size={28} />
              <b>{t("emptyTitle")}</b>
              <span>{t("emptyTasks")}</span>
            </div>
          ) : (
            <JourneyRoad
              actionsFor={(item) => {
                const task = stageTasks.find((row) => row.id === item.id);
                if (!task) return [];
                return [
                  { icon: <Eye aria-hidden="true" size={12} />, title: t("viewTask"), onClick: () => setViewingTask(task) },
                  {
                    icon: <BookOpen aria-hidden="true" size={12} />,
                    title: t("sourceAction"),
                    disabled: !task.sources || task.sources.length === 0,
                    onClick: () => setViewingTask(task),
                  },
                  { icon: <Pencil aria-hidden="true" size={12} />, title: t("edit"), disabled: readOnly, onClick: () => openEdit(task) },
                  { icon: <Copy aria-hidden="true" size={12} />, title: t("duplicate"), disabled: readOnly, onClick: () => setDuplicatingTask(task) },
                  {
                    icon: <Trash2 aria-hidden="true" size={12} />,
                    title: t("delete"),
                    tone: "danger" as const,
                    disabled: readOnly,
                    onClick: () => setDeletingTask(task),
                  },
                ];
              }}
              items={roadItems}
              labels={{ start: t("start"), finish: t("finish"), taskNo: (n) => t("taskNo", { n }) }}
              onOpen={(item) => {
                const task = stageTasks.find((row) => row.id === item.id);
                if (task) setViewingTask(task);
              }}
            />
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
            {readOnly ? <span className={styles.legendNote}>{t("versions.readonly")}</span> : null}
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
          {viewingTask.sources && viewingTask.sources.length > 0 ? (
            <section className={styles.viewSection}>
              <h3>
                <BookOpen aria-hidden="true" size={14} /> {t("view.sources")}
              </h3>
              <TaskSources sources={viewingTask.sources} />
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

      {creatingDraft && selectedVersion ? (
        <ConfirmModal
          body={t("versions.createDraftBody")}
          busy={busy === "version"}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={GitBranchPlus}
          confirmLabel={t("versions.createDraftConfirm")}
          icon={GitBranchPlus}
          onCancel={() => setCreatingDraft(false)}
          onConfirm={() => void handleCreateDraft()}
          title={t("versions.createDraftTitle", {
            n: Math.max(0, ...stageVersions.map((v) => v.version_no)) + 1,
            from: selectedVersion.version_no,
          })}
          tone="blue"
        />
      ) : null}

      {applying ? (
        <ConfirmModal
          body={
            applying.preview
              ? t("apply.body", {
                  modified: applying.preview.modified,
                  added: applying.preview.added,
                  removed: applying.preview.removed,
                  employees: applying.preview.employee_count,
                })
              : t("loading")
          }
          busy={busy === "apply" || applying.preview === null}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={CheckCircle2}
          confirmLabel={t("apply.confirm")}
          icon={CheckCircle2}
          onCancel={() => setApplying(null)}
          onConfirm={handleConfirmApply}
          title={t("apply.title", { n: applying.version.version_no, day: selectedStage?.title ?? "" })}
          tone="teal"
        />
      ) : null}

      {deletingVersion ? (
        <ConfirmModal
          body={t("versions.deleteBody")}
          busy={busy === "deleteVersion"}
          cancelLabel={t("cancel")}
          closeLabel={t("close")}
          confirmIcon={Trash2}
          confirmLabel={t("versions.deleteConfirm")}
          danger
          icon={Trash2}
          onCancel={() => setDeletingVersion(null)}
          onConfirm={handleConfirmDeleteVersion}
          title={t("versions.deleteTitle", { n: deletingVersion.version_no })}
        />
      ) : null}

      {rolloutVersion ? (
        <RolloutModal onClose={() => setRolloutVersion(null)} versionId={rolloutVersion.id} versionNo={rolloutVersion.version_no} />
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
