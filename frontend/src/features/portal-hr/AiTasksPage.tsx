"use client";

import {
  Check,
  ChevronDown,
  FileText,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, Fragment, useEffect, useRef, useState } from "react";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { useSession } from "@/features/auth/SessionProvider";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  AiProposalDocumentResultDTO,
  AiTaskProposalResponseDTO,
  DocumentListItemResponseDTO,
  JobResponseDTO,
  StageOptionResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { AiRoadmapReview, nextReviewKey, type Review } from "./AiRoadmapReview";
import { categoryStyle } from "./docCategory";
import styles from "./AiTasksPage.module.scss";
import { ProposalProgress } from "./ProposalProgress";
import { SectionNotice } from "./SectionNotice";
import { useJob } from "./useJob";

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) return t(`errors.${error.code}`);
  return t("errors.unavailable");
}

const DOCUMENT_ERRORS = new Set(["AI_INVALID_JSON", "LLM_UNAVAILABLE", "DOCUMENT_VERSION_NOT_FOUND"]);
const JOB_ERRORS = new Set(["LLM_NOT_CONFIGURED", "NO_DOCUMENTS", "JOB_ERROR", "JOB_INTERRUPTED"]);

/** Gom đề xuất của nhiều tài liệu theo thứ tự tài liệu, bỏ đề xuất trùng tên (giữ cái đầu tiên); nhớ đề xuất lấy từ tài liệu nào. */
function mergeProposals(
  documents: AiProposalDocumentResultDTO[],
): { proposal: AiTaskProposalResponseDTO; origin: NonNullable<Review["origin"]> }[] {
  const merged: { proposal: AiTaskProposalResponseDTO; origin: NonNullable<Review["origin"]> }[] = [];
  for (const entry of documents) {
    for (const proposal of entry.proposals) {
      if (merged.some((item) => item.proposal.title === proposal.title)) continue;
      merged.push({
        proposal,
        origin: { versionId: entry.version_id, title: entry.document_title, label: entry.version_label },
      });
    }
  }
  return merged;
}

const TILE_TONES = ["tone0", "tone1", "tone2", "tone3"] as const;
// Biểu tượng theo thứ tự ô giai đoạn, đúng v15: flag / users / sparkles / shield.
const TILES: { icon: FlatIconName; tone: FlatTone }[] = [
  { icon: "flag", tone: "red" },
  { icon: "users", tone: "teal" },
  { icon: "sparkle", tone: "violet" },
  { icon: "award", tone: "amber" },
];
// Thanh bước: mỗi bước một biểu tượng và một màu riêng (xanh dương, chàm, xanh ngọc, hổ phách) cho dễ phân biệt.
const STEP_FLAT: { icon: FlatIconName; tone: FlatTone }[] = [
  { icon: "file", tone: "blue" },
  { icon: "sparkle", tone: "indigo" },
  { icon: "check", tone: "teal" },
  { icon: "tasks", tone: "amber" },
];

/** "Tạo task bằng AI" thật — cổng đúng cấu trúc/DOM prototype v15 (.ai14-steps/.ai14-source-card/
 * .ai14-config/.ai14-days/.ai14-run) trích từ DOM đã render thật, chỉ dùng dữ liệu thật (tài liệu đã
 * upload + giai đoạn đã có qua GET /portal/stages, không có "Ngày 1/2/3-5" giả). */
export function AiTasksPage() {
  const t = useTranslations("portalHr");
  const { user } = useSession();

  const [documents, setDocuments] = useState<DocumentListItemResponseDTO[] | null>(null);
  const [stages, setStages] = useState<StageOptionResponseDTO[] | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [newStageOpen, setNewStageOpen] = useState(false);

  // v15 cho chọn nhiều tài liệu nguồn cho một lần phân tích.
  const [selectedDocs, setSelectedDocs] = useState<DocumentListItemResponseDTO[]>([]);
  const [pickerQuery, setPickerQuery] = useState("");
  const [selectedStageId, setSelectedStageId] = useState<number | null>(null);

  const [newTemplateTitle, setNewTemplateTitle] = useState("Lộ trình onboarding");
  const [newStageTitle, setNewStageTitle] = useState("Ngày 1");

  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [docResults, setDocResults] = useState<AiProposalDocumentResultDTO[]>([]);
  const [proposalJobId, setProposalJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [acceptedCount, setAcceptedCount] = useState(0);
  // Đang tạo task thật sau khi HR duyệt: số đã tạo / tổng, để hiện "Đang tạo task 3/16".
  const [creating, setCreating] = useState<{ done: number; total: number } | null>(null);
  // Task đã tạo trong lượt này (tên → mã) để đổi "tiên quyết theo tên" của AI thành tiên quyết thật khi tạo tiếp.
  const createdByTitle = useRef(new Map<string, number>());
  // Thứ tự mục của từng phiên bản tài liệu (tải một lần) để chèn task mới đúng chỗ; và bản mới nhất của roadmap cho hàm bất đồng bộ.
  const sectionOrders = useRef(new Map<number, number[]>());
  const reviewsRef = useRef<Review[] | null>(null);

  function finishProposalJob(job: JobResponseDTO) {
    setBusy((current) => (current === "propose" ? null : current));
    if (job.status === "FAILED") {
      const code = (job.error ?? "").split(":")[0];
      setError(JOB_ERRORS.has(code) ? t(`run.errors.${code}`) : t("errors.unavailable"));
      return;
    }
    const documents = ((job.result?.documents as AiProposalDocumentResultDTO[] | undefined) ?? []).filter(Boolean);
    setDocResults(documents);
    createdByTitle.current = new Map();
    setReviews(
      mergeProposals(documents).map(({ proposal, origin }) => ({
        key: nextReviewKey(),
        proposal,
        status: "pending" as const,
        origin,
      })),
    );
    setAcceptedCount(0);
  }

  useEffect(() => {
    reviewsRef.current = reviews;
  }, [reviews]);

  const proposalJob = useJob(proposalJobId, finishProposalJob);

  function loadDocs() {
    portalHrApi
      .listDocuments()
      .then((result) => setDocuments(result))
      .catch((caught: unknown) => setError(errorMessage(t, caught)));
  }
  function loadStages() {
    portalHrApi
      .listStageOptions()
      .then((result) => {
        setStages(result);
        // Như v15 (mặc định chọn Ngày 1): luôn có một giai đoạn đích được chọn sẵn.
        setSelectedStageId((current) => current ?? result[0]?.id ?? null);
      })
      .catch((caught: unknown) => setError(errorMessage(t, caught)));
  }

  useEffect(() => {
    loadDocs();
    loadStages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Tải lại trang hoặc quay lại giữa chừng: nếu còn một lượt tạo task đang chạy nền thì theo dõi tiếp thay vì bắt chạy lại.
  useEffect(() => {
    let cancelled = false;
    Promise.resolve(portalHrApi.listActiveJobs("AI_TASK_PROPOSAL"))
      .then((jobs) => {
        const running = Array.isArray(jobs) ? jobs[0] : undefined;
        if (cancelled || !running) return;
        setProposalJobId((current) => current ?? running.id);
        setBusy((current) => current ?? "propose");
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Bước 1 tới khi bấm phân tích; đang chạy là "AI dựng roadmap"; có đề xuất là "HR chấp nhận"; đã chấp nhận là bước cuối.
  const stepIndex = reviews !== null ? (acceptedCount > 0 && reviews.length === 0 ? 3 : 2) : busy === "propose" ? 1 : 0;

  const readyDocs = (documents ?? []).filter((d) => d.latest_version_id !== null && d.status === "ACTIVE");
  const pickerDocs = readyDocs.filter((d) => {
    const q = pickerQuery.trim().toLowerCase();
    return !q || d.title.toLowerCase().includes(q) || d.category_name.toLowerCase().includes(q) || (d.owner_name ?? "").toLowerCase().includes(q);
  });

  function toggleDoc(doc: DocumentListItemResponseDTO) {
    setSelectedDocs((current) =>
      current.some((d) => d.id === doc.id) ? current.filter((d) => d.id !== doc.id) : [...current, doc],
    );
  }

  function openNewStage() {
    setNewStageTitle(`Ngày ${(stages?.length ?? 0) + 1}`);
    setError(null);
    setNewStageOpen(true);
  }

  async function handleCreateStage(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy("stage");
    try {
      // Đã có lộ trình nháp: thêm ngày mới vào đó. Chưa có: tạo lộ trình mới (mã do hệ thống sinh, không bắt người dùng nhập).
      const existing = stages?.[0];
      const template = existing
        ? { id: existing.journey_template_id, title: existing.template_title }
        : await portalHrApi.createJourneyTemplate({ code: "tpl-" + Date.now().toString(36), title: newTemplateTitle });
      const stage = await portalHrApi.createJourneyStage(template.id, {
        title: newStageTitle,
        sort_order: (stages?.length ?? 0) + 1,
      });
      setStages((current) => [
        ...(current ?? []),
        { id: stage.id, journey_template_id: template.id, title: stage.title, template_title: template.title },
      ]);
      setSelectedStageId(stage.id);
      setNewStageOpen(false);
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handlePropose(onlyVersionIds?: number[]) {
    const versionIds =
      onlyVersionIds ?? selectedDocs.map((d) => d.latest_version_id).filter((id): id is number => id !== null);
    if (versionIds.length === 0) return;
    setError(null);
    setBusy("propose");
    try {
      // Chạy nền có phần trăm (mục 14.5): backend trả job_id ngay, giao diện hỏi tiến độ mỗi giây.
      const job = await portalHrApi.createAiTaskProposalJob({ document_version_ids: versionIds });
      setReviews(null);
      setDocResults([]);
      setProposalJobId(job.id);
    } catch (caught) {
      setError(errorMessage(t, caught));
      setBusy(null);
    }
  }

  async function acceptOne(proposal: AiTaskProposalResponseDTO): Promise<boolean> {
    if (!selectedStageId) return false;
    try {
      const dependsOn = (proposal.prerequisites ?? [])
        .map((name) => createdByTitle.current.get(name))
        .filter((id): id is number => id !== undefined);
      const created = await portalHrApi.acceptAiTaskProposal(selectedStageId, {
        title: proposal.title,
        instructions_markdown: proposal.instructions_markdown,
        required: true,
        source_chunks: proposal.source_chunks,
        summary: proposal.summary,
        done_criteria: proposal.done_criteria,
        estimated_minutes: proposal.estimated_minutes,
        warnings: proposal.warnings,
        task_group: proposal.task_group ?? null,
        depends_on: dependsOn,
      });
      createdByTitle.current.set(proposal.title, created.id);
      return true;
    } catch (caught) {
      setError(errorMessage(t, caught));
      return false;
    }
  }

  /** "Thêm vào Quản lý task": chỉ lúc này task thật mới được tạo, theo đúng thứ tự trên roadmap; lỗi thì dừng và giữ phần còn lại. */
  async function handleCreateTasks() {
    if (!reviews || !selectedStageId) return;
    setError(null);
    setNotice(null);
    setBusy("accept-all");
    let created = 0;
    const remaining = [...reviews];
    const total = remaining.length;
    setCreating({ done: 0, total });
    while (remaining.length > 0) {
      const next = remaining[0]!;
      if (!(await acceptOne(next.proposal))) break;
      remaining.shift();
      created += 1;
      setCreating({ done: created, total });
    }
    setCreating(null);
    setReviews(remaining);
    if (created > 0) {
      setAcceptedCount((n) => n + created);
      setNotice(t("propose.acceptedAll", { count: created }));
    }
    setBusy(null);
  }

  /** Chèn task do AI soạn cho mục HR chọn vào roadmap ĐÚNG VỊ TRÍ theo thứ tự mục trong tài liệu (không dồn xuống cuối), rồi báo
   * đã thêm vào task thứ mấy. HR vẫn bấm "Thêm vào Quản lý task" như mọi thẻ khác. Bỏ trùng tên với task đang có. */
  async function addSectionProposals(
    entry: AiProposalDocumentResultDTO,
    sectionId: number,
    proposals: AiTaskProposalResponseDTO[],
  ): Promise<boolean> {
    const current = reviewsRef.current ?? [];
    const existing = new Set(current.map((review) => review.proposal.title));
    const fresh = proposals.filter((proposal) => !existing.has(proposal.title));
    if (fresh.length === 0) {
      setNotice(t("result.section.duplicate"));
      return false;
    }
    let order = sectionOrders.current.get(entry.version_id);
    if (!order) {
      order = await portalHrApi.getDocumentSectionOrder(entry.version_id).catch(() => []);
      sectionOrders.current.set(entry.version_id, order);
    }
    const rank = (id: number) => order.indexOf(id);
    const wanted = rank(sectionId);
    const origin = { versionId: entry.version_id, title: entry.document_title, label: entry.version_label };
    const latest = reviewsRef.current ?? [];
    // Thứ tự một thẻ cũ trong tài liệu = mục sớm nhất nó trích; thẻ chưa biết thì bỏ qua khi tìm chỗ chèn.
    const rankOf = (review: Review) => {
      const ranks = review.proposal.source_chunks.map((chunk) => rank(chunk.document_section_id)).filter((n) => n >= 0);
      return ranks.length > 0 ? Math.min(...ranks) : null;
    };
    let at = latest.length;
    if (wanted >= 0) {
      const sameDoc = latest
        .map((review, index) => ({ index, review, place: review.origin?.versionId === entry.version_id ? rankOf(review) : null }))
        .filter((item) => item.place !== null);
      const after = sameDoc.find((item) => (item.place as number) > wanted);
      if (after) at = after.index;
      else if (sameDoc.length > 0) at = sameDoc[sameDoc.length - 1]!.index + 1;
    }
    const added = fresh.map((proposal) => ({ key: nextReviewKey(), proposal, status: "pending" as const, origin }));
    setReviews([...latest.slice(0, at), ...added, ...latest.slice(at)]);
    setNotice(t("result.section.added", { position: at + 1, title: fresh[0]!.title, count: fresh.length }));
    return true;
  }

  function resetReview() {
    createdByTitle.current = new Map();
    setReviews(null);
    setDocResults([]);
    setNotice(null);
    setAcceptedCount(0);
  }

  const runLabel =
    selectedDocs.length === 0
      ? t("run.needDoc")
      : !selectedStageId
        ? t("run.needStage")
        : busy === "propose"
          ? t("run.loading")
          : t("run.submitCount", { count: selectedDocs.length });

  return (
    <div className={styles.page}>
      <header className={styles.pagehead}>
        <div className={styles.pageheadInner}>
          <span className={styles.phi}>
            <FlatIcon name="sparkle" size={28} tone="violet" />
          </span>
          <div className={styles.pageheadText}>
            <h1>{t("title")}</h1>
            <p>{t("description")}</p>
          </div>
        </div>
        <span className={styles.safe}>
          <ShieldCheck aria-hidden="true" size={14} /> {t("safeBadge")}
        </span>
      </header>

      <ol className={styles.steps}>
        {["step1", "step2", "step3", "step4"].map((key, i) => {
          const flat = STEP_FLAT[i] ?? { icon: "file" as const, tone: "blue" as const };
          const state = i === stepIndex ? styles.stepOn : i < stepIndex ? styles.stepDone : "";
          return (
            <Fragment key={key}>
              <li aria-current={i === stepIndex ? "step" : undefined} className={`${styles[`stepTone${i}`]} ${state}`}>
                <b>
                  {i < stepIndex ? <Check aria-hidden="true" size={14} /> : <FlatIcon name={flat.icon} size={17} tone={flat.tone} />}
                </b>{" "}
                {t(`steps.${key}`)}
              </li>
              {i < 3 ? (
                <li
                  aria-hidden="true"
                  className={`${styles.stepLine} ${styles[`stepTone${i}`]} ${i < stepIndex ? styles.stepLineDone : ""}`}
                />
              ) : null}
            </Fragment>
          );
        })}
      </ol>

      {error ? <p className={styles.banner + " " + styles.bannerError}>{error}</p> : null}
      {notice ? <p className={styles.banner + " " + styles.bannerOk}>{notice}</p> : null}

      <div className={`${styles.grid21} ${styles.layout}`}>
        <div className={styles.sourceCard}>
          <div className={styles.cardHead}>
            <div className={styles.chh}>
              <span className={`${styles.ichip} ${styles.toneBlue}`}>
                <FlatIcon name="file" size={20} tone="blue" />
              </span>
              <h2>{t("document.heading")}</h2>
              <small>{t("document.selectedCount", { count: selectedDocs.length })}</small>
            </div>
            <button className={styles.btnSecSm} onClick={() => setPickerOpen((v) => !v)} type="button">
              {pickerOpen ? <ChevronDown aria-hidden="true" size={13} /> : <Plus aria-hidden="true" size={13} />}{" "}
              {pickerOpen ? t("document.collapse") : t("document.pick")}
            </button>
          </div>
          <div className={styles.cardBody}>
            {selectedDocs.length > 0 || !pickerOpen ? (
              <div className={`${styles.selectedList} ${selectedDocs.length ? styles.has : styles.selectedEmpty}`}>
              {selectedDocs.length ? (
                selectedDocs.map((doc) => (
                  <span className={styles.selectedChip} key={doc.id}>
                    <FileText aria-hidden="true" size={12} />
                    {doc.title}
                    <button aria-label={t("document.remove")} onClick={() => toggleDoc(doc)} type="button">
                      <X aria-hidden="true" size={12} />
                    </button>
                  </span>
                ))
              ) : (
                <span className={styles.emptyDocs}>
                  <i>
                    <FlatIcon name="file" size={34} tone="blue" />
                  </i>
                  <b>{t("document.empty")}</b>
                  <small>{t("document.emptyHint")}</small>
                </span>
              )}
              </div>
            ) : null}

            {pickerOpen ? (
              <div className={styles.picker}>
                <div className={styles.pickerTitle}>
                  <div>
                    <b>{t("document.pickerTitle")}</b>
                    <small>{t("document.pickerHint")}</small>
                  </div>
                  <span>{t("document.pickedBadge", { count: selectedDocs.length })}</span>
                </div>
                <div className={styles.pickerSearch}>
                  <Search aria-hidden="true" size={14} />
                  <input
                    onChange={(e) => setPickerQuery(e.target.value)}
                    placeholder={t("document.searchPlaceholder")}
                    value={pickerQuery}
                  />
                </div>
                <div className={styles.pickerList}>
                  {documents === null ? (
                    <p className={styles.faint}>{t("document.loading")}</p>
                  ) : pickerDocs.length === 0 ? (
                    <p className={styles.faint}>{t("document.noneAvailable")}</p>
                  ) : (
                    pickerDocs.map((doc) => {
                      const cat = categoryStyle(doc.category_name, 19);
                      const picked = selectedDocs.some((d) => d.id === doc.id);
                      return (
                        <button
                          className={`${styles.docRow} ${styles[`doc_${cat.tone}`]} ${picked ? styles.docOn : ""}`}
                          key={doc.id}
                          onClick={() => toggleDoc(doc)}
                          type="button"
                        >
                          <span>{cat.icon}</span>
                          <span className={styles.docRowText}>
                            <b>{doc.title}</b>
                            <small>
                              <i>{doc.category_name}</i> {t("sectionCount", { count: doc.section_count })}
                              {doc.owner_name ? ` · ${doc.owner_name}` : ""}
                            </small>
                            {doc.source_key ? <p>{doc.source_key}</p> : null}
                          </span>
                          {picked ? <Check aria-hidden="true" size={16} /> : null}
                        </button>
                      );
                    })
                  )}
                </div>
                <div className={styles.pickerFoot}>
                  <span>
                    <Check aria-hidden="true" size={13} /> {t("document.pickedFoot", { count: selectedDocs.length })}
                  </span>
                  <button className={styles.btnSm} onClick={() => setPickerOpen(false)} type="button">
                    {t("document.done")}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className={styles.configCard}>
          <div className={styles.cardHead}>
            <div className={styles.chh}>
              <span className={`${styles.ichip} ${styles.toneIndigo}`}>
                <FlatIcon name="route" size={20} tone="indigo" />
              </span>
              <h2>{t("stage.heading")}</h2>
              <small>{t("stage.hint")}</small>
            </div>
          </div>
          <div className={styles.cardBody}>
            <div className={styles.dayGrid}>
              {(stages ?? []).map((stage, i) => {
                const tile = TILES[i % TILES.length] ?? TILES[0]!;
                return (
                  <button
                    className={`${styles.day} ${selectedStageId === stage.id ? styles.dayOn : ""} ${styles[TILE_TONES[i % 4]]}`}
                    key={stage.id}
                    onClick={() => setSelectedStageId(stage.id)}
                    type="button"
                  >
                    <span>
                      <FlatIcon name={tile.icon} size={20} tone={tile.tone} />
                    </span>
                    <span className={styles.dayText}>
                      <b>{stage.title}</b>
                      <small>{stage.template_title}</small>
                      <small>
                        {stage.draft_version_no
                          ? t("stage.toDraft", { n: stage.draft_version_no })
                          : t("stage.toNewDraft")}
                      </small>
                    </span>
                    {selectedStageId === stage.id ? <Check aria-hidden="true" size={15} /> : null}
                  </button>
                );
              })}
            </div>

            {stages !== null && stages.length === 0 ? <p className={styles.noStages}>{t("stage.empty")}</p> : null}

            <button className={styles.newDay} onClick={openNewStage} type="button">
              <Plus aria-hidden="true" size={15} />
              <span>
                <b>{stages !== null && stages.length === 0 ? t("stage.createFirst") : t("stage.addNew")}</b>
                <small>{t("stage.addNewHint")}</small>
              </span>
            </button>

            <div className={styles.audience}>
              <span>
                <FlatIcon name="building" size={22} tone="indigo" />
              </span>
              <div>
                <small>{t("audience.label")}</small>
                <b>{user.department ?? t("audience.fallback")}</b>
                <em>{t("audience.sub")}</em>
              </div>
            </div>

            <button
              className={styles.run}
              disabled={selectedDocs.length === 0 || !selectedStageId || busy === "propose"}
              onClick={() => handlePropose()}
              type="button"
            >
              <Sparkles aria-hidden="true" size={15} /> {runLabel}
            </button>
            {creating !== null || (proposalJobId !== null && busy === "propose") ? (
              <ProposalProgress creating={creating} job={proposalJob.job} lost={proposalJob.lost} />
            ) : null}
            <p className={styles.hint}>
              <ShieldCheck aria-hidden="true" size={12} /> {t("run.footnote")}
            </p>
          </div>
        </div>
      </div>

      {newStageOpen ? (
        <PortalModal
          closeLabel={t("stage.close")}
          footer={
            <>
              <button className={m.btnSec} onClick={() => setNewStageOpen(false)} type="button">
                {t("stage.cancel")}
              </button>
              <button className={m.btn} disabled={busy === "stage"} form="new-stage-form" type="submit">
                <Plus aria-hidden="true" size={14} /> {t("stage.create")}
              </button>
            </>
          }
          icon={Plus}
          onClose={() => setNewStageOpen(false)}
          subtitle={t("stage.addNewHint")}
          title={t("stage.addNew")}
          tone="indigo"
        >
          <form id="new-stage-form" onSubmit={handleCreateStage}>
            {error ? <p className={`${styles.banner} ${styles.bannerError}`}>{error}</p> : null}
            <div className={m.fgrid}>
              <div className={m.span2}>
                <label htmlFor="new-stage-title">{t("stage.title")}</label>
                <input
                  autoFocus
                  id="new-stage-title"
                  onChange={(e) => setNewStageTitle(e.target.value)}
                  required
                  type="text"
                  value={newStageTitle}
                />
              </div>
              {stages !== null && stages.length > 0 ? null : (
                <div className={m.span2}>
                  <label htmlFor="new-template-title">{t("template.title")}</label>
                  <input
                    id="new-template-title"
                    onChange={(e) => setNewTemplateTitle(e.target.value)}
                    required
                    type="text"
                    value={newTemplateTitle}
                  />
                </div>
              )}
            </div>
          </form>
        </PortalModal>
      ) : null}

      {docResults.length > 0 ? (
        <ul aria-label={t("result.heading")} className={styles.docResults}>
          {docResults.map((entry) => (
            <li data-status={entry.status} key={entry.version_id}>
              <b>{entry.document_title}</b>
              <small>{entry.version_label}</small>
              <span>
                {entry.status === "DONE"
                  ? t("result.done", { count: entry.proposals.length })
                  : DOCUMENT_ERRORS.has(entry.error ?? "")
                    ? t(`result.errors.${entry.error}`)
                    : t("result.failed")}
              </span>
              {entry.truncated_sections ? (
                <em>{t("result.truncated", { count: entry.truncated_sections })}</em>
              ) : null}
              {entry.uncovered_sections && entry.uncovered_sections.length > 0 ? (
                <SectionNotice
                  disabled={busy !== null}
                  documentTitle={entry.document_title}
                  kind="uncovered"
                  onAdd={(sectionId, proposals) => addSectionProposals(entry, sectionId, proposals)}
                  sections={entry.uncovered_sections}
                  versionId={entry.version_id}
                  versionLabel={entry.version_label}
                />
              ) : null}
              {entry.skipped_info_sections && entry.skipped_info_sections.length > 0 ? (
                <SectionNotice
                  disabled={busy !== null}
                  documentTitle={entry.document_title}
                  kind="skippedInfo"
                  onAdd={(sectionId, proposals) => addSectionProposals(entry, sectionId, proposals)}
                  sections={entry.skipped_info_sections}
                  versionId={entry.version_id}
                  versionLabel={entry.version_label}
                />
              ) : null}
              {entry.status === "FAILED" ? (
                <button
                  className={styles.btnSm}
                  disabled={busy === "propose"}
                  onClick={() => handlePropose([entry.version_id])}
                  type="button"
                >
                  {t("result.retry")}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {reviews ? (
        <AiRoadmapReview
          busy={busy !== null}
          dayTitle={stages?.find((stage) => stage.id === selectedStageId)?.title ?? ""}
          onChange={setReviews}
          onCreate={handleCreateTasks}
          onReset={resetReview}
          reviews={reviews}
        />
      ) : null}
    </div>
  );
}
