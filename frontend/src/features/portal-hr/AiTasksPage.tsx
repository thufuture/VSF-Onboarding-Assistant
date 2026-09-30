"use client";

import {
  Check,
  CheckCircle2,
  ChevronDown,
  FileText,
  Flag,
  Layers,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, Fragment, useEffect, useState } from "react";

import { useSession } from "@/features/auth/SessionProvider";
import { portalHrApi, PortalError } from "@/features/portal-hr/api";
import type {
  AiTaskProposalResponseDTO,
  DocumentListItemResponseDTO,
  StageOptionResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { categoryStyle } from "./docCategory";
import styles from "./AiTasksPage.module.scss";

function errorMessage(t: (key: string) => string, error: unknown): string {
  if (error instanceof PortalError) return t(`errors.${error.code}`);
  return t("errors.unavailable");
}

const TILE_TONES = ["tone0", "tone1", "tone2", "tone3"] as const;
// Biểu tượng theo thứ tự ô giai đoạn, đúng v15: flag / users / sparkles / shield.
const TILE_ICONS = [Flag, Users, Sparkles, ShieldCheck];

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

  const [newTemplateCode, setNewTemplateCode] = useState(() => "tpl-" + Date.now().toString(36));
  const [newTemplateTitle, setNewTemplateTitle] = useState("Lộ trình onboarding");
  const [newStageTitle, setNewStageTitle] = useState("Ngày 1");

  const [proposals, setProposals] = useState<AiTaskProposalResponseDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [acceptedCount, setAcceptedCount] = useState(0);

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

  // Như v15: bước 1 giữ nguyên tới khi bấm phân tích; có đề xuất là bước "HR chấp nhận", đã chấp nhận là bước cuối.
  const stepIndex = proposals !== null ? (acceptedCount > 0 ? 3 : 2) : 0;

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

  async function handleCreateStage(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy("stage");
    try {
      const template = await portalHrApi.createJourneyTemplate({ code: newTemplateCode, title: newTemplateTitle });
      const stage = await portalHrApi.createJourneyStage(template.id, { title: newStageTitle, sort_order: 1 });
      setStages((current) => [
        ...(current ?? []),
        { id: stage.id, journey_template_id: template.id, title: stage.title, template_title: template.title },
      ]);
      setSelectedStageId(stage.id);
      setNewStageOpen(false);
      setNewTemplateCode("tpl-" + Date.now().toString(36));
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handlePropose() {
    const versionIds = selectedDocs.map((d) => d.latest_version_id).filter((id): id is number => id !== null);
    if (versionIds.length === 0) return;
    setError(null);
    setBusy("propose");
    try {
      // API đề xuất theo từng phiên bản tài liệu: gọi lần lượt rồi gộp, bỏ đề xuất trùng tên.
      const merged: AiTaskProposalResponseDTO[] = [];
      for (const versionId of versionIds) {
        const part = await portalHrApi.proposeAiTasks({ document_version_id: versionId });
        for (const proposal of part) {
          if (!merged.some((item) => item.title === proposal.title)) merged.push(proposal);
        }
      }
      setProposals(merged);
      setAcceptedCount(0);
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleAccept(proposal: AiTaskProposalResponseDTO) {
    if (!selectedStageId) return;
    setError(null);
    setBusy(`accept-${proposal.title}`);
    try {
      const result = await portalHrApi.acceptAiTaskProposal(selectedStageId, {
        title: proposal.title,
        instructions_markdown: proposal.instructions_markdown,
        required: true,
        source_chunks: proposal.source_chunks,
      });
      setNotice(t("propose.accepted", { id: result.id }));
      setAcceptedCount((n) => n + 1);
      setProposals((current) => (current ? current.filter((item) => item !== proposal) : current));
    } catch (caught) {
      setError(errorMessage(t, caught));
    } finally {
      setBusy(null);
    }
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
            <Sparkles aria-hidden="true" size={22} />
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
        {["step1", "step2", "step3", "step4"].map((key, i) => (
          <Fragment key={key}>
            <li className={i === stepIndex ? styles.stepOn : ""}>
              <b>{i + 1}</b> {t(`steps.${key}`)}
            </li>
            {i < 3 ? <li aria-hidden="true" className={styles.stepLine} /> : null}
          </Fragment>
        ))}
      </ol>

      {error ? <p className={styles.banner + " " + styles.bannerError}>{error}</p> : null}
      {notice ? <p className={styles.banner + " " + styles.bannerOk}>{notice}</p> : null}

      <div className={`${styles.grid21} ${styles.layout}`}>
        <div className={styles.sourceCard}>
          <div className={styles.cardHead}>
            <div className={styles.chh}>
              <span className={`${styles.ichip} ${styles.toneBlue}`}>
                <FileText aria-hidden="true" size={15} />
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
            <div className={`${styles.selectedList} ${selectedDocs.length ? styles.has : ""}`}>
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
                <span className={styles.faint}>{t("document.empty")}</span>
              )}
            </div>

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
                <Layers aria-hidden="true" size={15} />
              </span>
              <h2>{t("stage.heading")}</h2>
              <small>{t("stage.hint")}</small>
            </div>
          </div>
          <div className={styles.cardBody}>
            <div className={styles.dayGrid}>
              {(stages ?? []).map((stage, i) => {
                const TileIcon = TILE_ICONS[i % TILE_ICONS.length];
                return (
                  <button
                    className={`${styles.day} ${selectedStageId === stage.id ? styles.dayOn : ""} ${styles[TILE_TONES[i % 4]]}`}
                    key={stage.id}
                    onClick={() => setSelectedStageId(stage.id)}
                    type="button"
                  >
                    <span>
                      <TileIcon aria-hidden="true" size={15} />
                    </span>
                    <span className={styles.dayText}>
                      <b>{stage.title}</b>
                      <small>{stage.template_title}</small>
                    </span>
                    {selectedStageId === stage.id ? <Check aria-hidden="true" size={15} /> : null}
                  </button>
                );
              })}
            </div>

            {newStageOpen ? (
              <form className={styles.newStageForm} onSubmit={handleCreateStage}>
                <label>
                  {t("template.code")}
                  <input onChange={(e) => setNewTemplateCode(e.target.value)} required value={newTemplateCode} />
                </label>
                <label>
                  {t("template.title")}
                  <input onChange={(e) => setNewTemplateTitle(e.target.value)} required value={newTemplateTitle} />
                </label>
                <label>
                  {t("stage.title")}
                  <input onChange={(e) => setNewStageTitle(e.target.value)} required value={newStageTitle} />
                </label>
                <button className={styles.btnSm} disabled={busy === "stage"} type="submit">
                  {t("stage.create")}
                </button>
              </form>
            ) : (
              <button className={styles.newDay} onClick={() => setNewStageOpen(true)} type="button">
                <Plus aria-hidden="true" size={15} />
                <span>
                  <b>{t("stage.addNew")}</b>
                  <small>{t("stage.addNewHint")}</small>
                </span>
              </button>
            )}

            <div className={styles.audience}>
              <span>
                <Layers aria-hidden="true" size={16} />
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
              onClick={handlePropose}
              type="button"
            >
              <Sparkles aria-hidden="true" size={15} /> {runLabel}
            </button>
            <p className={styles.hint}>
              <ShieldCheck aria-hidden="true" size={12} /> {t("run.footnote")}
            </p>
          </div>
        </div>
      </div>

      {proposals ? (
        <div className={styles.card}>
          <div className={styles.cardHead}>
            <div className={styles.chh}>
              <span className={`${styles.ichip} ${styles.toneAmber}`}>
                <Sparkles aria-hidden="true" size={15} />
              </span>
              <h2>{t("propose.heading")}</h2>
              <small>{t("propose.hint")}</small>
            </div>
          </div>
          <div className={styles.cardBody}>
            {proposals.length === 0 ? (
              <p className={styles.faint}>{t("propose.empty")}</p>
            ) : (
              <ul className={styles.proposalList}>
                {proposals.map((proposal) => (
                  <li className={styles.proposalCard} key={proposal.title}>
                    <div className={styles.proposalHead}>
                      <b>{proposal.title}</b>
                      <span className={styles.confidence} data-level={proposal.confidence}>
                        {t("propose.confidence")}: {proposal.confidence}
                      </span>
                    </div>
                    <p>{proposal.summary}</p>
                    <p className={styles.instructions}>{proposal.instructions_markdown}</p>
                    <p className={styles.sourcesLabel}>{t("propose.sources")}:</p>
                    <ul className={styles.sourceList}>
                      {proposal.source_chunks.map((chunk) => (
                        <li key={chunk.document_section_id}>“{chunk.quote}”</li>
                      ))}
                    </ul>
                    <button
                      className={styles.btnSm}
                      disabled={busy === `accept-${proposal.title}`}
                      onClick={() => handleAccept(proposal)}
                      type="button"
                    >
                      <CheckCircle2 aria-hidden="true" size={14} /> {t("propose.accept")}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
