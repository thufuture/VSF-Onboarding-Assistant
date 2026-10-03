"use client";

import { Check, CheckCircle2, Clock, Copy, Eye, Pencil, Send, Sparkles, Trash2, TriangleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { ConfirmModal, modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { JourneyRoad, type RoadItem } from "@/components/roadmap/JourneyRoad";
import { TaskSources } from "@/components/task-sources/TaskSources";
import type { AiTaskProposalResponseDTO, TaskSourceDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./AiRoadmapReview.module.scss";

export type ReviewStatus = "pending" | "accepted" | "edited";
export type Review = {
  key: number;
  proposal: AiTaskProposalResponseDTO;
  status: ReviewStatus;
  /** Tài liệu mà đề xuất lấy từ (để mở đúng đoạn nguồn trong tài liệu). */
  origin?: { versionId: number; title: string; label: string };
};

/** Nguồn của một đề xuất dưới dạng danh sách nguồn dùng chung (mỗi trích dẫn một nguồn, kèm mục chứa nó). */
function sourcesOf(review: Review): TaskSourceDTO[] {
  const origin = review.origin;
  if (!origin) return [];
  return review.proposal.source_chunks.map((chunk) => ({
    document_title: origin.title,
    version_label: origin.label,
    version_id: origin.versionId,
    document_url: "",
    section_heading: chunk.heading ?? null,
    quote: chunk.quote,
  }));
}

let reviewSeq = 0;
/** Mã cục bộ cho một đề xuất (chưa có task thật nên chưa có id từ máy chủ). */
export function nextReviewKey(): number {
  reviewSeq += 1;
  return reviewSeq;
}

type Dialog =
  | { kind: "source"; key: number }
  | { kind: "edit"; key: number }
  | { kind: "remove"; key: number };

/**
 * Bước "HR chấp nhận" của Tạo task bằng AI (prototype v15, `aiRoadmapReview14`): các đề xuất hiện thành roadmap giống trang Quản lý
 * task (dùng chung `JourneyRoad`), mỗi thẻ có chấp nhận, xem đúng đoạn nguồn, sửa, nhân bản, bỏ. Chấp nhận chỉ đánh dấu trên trang này;
 * task thật chỉ được tạo khi bấm "Thêm vào Quản lý task" sau khi không còn đề xuất chờ xem.
 */
export function AiRoadmapReview({
  reviews,
  onChange,
  dayTitle,
  busy,
  onCreate,
  onReset,
}: {
  reviews: Review[];
  onChange: (next: Review[]) => void;
  dayTitle: string;
  busy: boolean;
  onCreate: () => void;
  onReset: () => void;
}) {
  const t = useTranslations("portalHr.propose");
  const tm = useTranslations("portalHr");
  const [dialog, setDialog] = useState<Dialog | null>(null);

  const pending = reviews.filter((r) => r.status === "pending").length;
  const accepted = reviews.length - pending;
  const current = dialog ? reviews.find((r) => r.key === dialog.key) : undefined;

  const setStatus = (key: number, status: ReviewStatus) =>
    onChange(reviews.map((r) => (r.key === key ? { ...r, status } : r)));

  const items: RoadItem[] = reviews.map((r) => ({
    id: r.key,
    title: r.proposal.title,
    group: r.proposal.task_group ?? null,
    pill: t(`status.${r.status}`),
    chips: [
      {
        icon: <Clock aria-hidden="true" size={11} />,
        label: r.proposal.estimated_minutes ? t("minutes", { n: r.proposal.estimated_minutes }) : "—",
      },
      { icon: <Sparkles aria-hidden="true" size={11} />, label: t(`confidenceLevel.${r.proposal.confidence}`) },
      ...(r.proposal.review_notes && r.proposal.review_notes.length > 0
        ? [{ icon: <TriangleAlert aria-hidden="true" size={11} />, label: t("needsCheck") }]
        : []),
    ],
  }));

  function duplicate(key: number) {
    const index = reviews.findIndex((r) => r.key === key);
    const source = reviews[index];
    if (!source) return;
    const copy: Review = {
      key: nextReviewKey(),
      proposal: { ...source.proposal, title: `${source.proposal.title} ${t("copySuffix")}` },
      status: "pending",
    };
    onChange([...reviews.slice(0, index + 1), copy, ...reviews.slice(index + 1)]);
  }

  return (
    <section className={styles.review}>
      <div className={styles.summary}>
        <div>
          <span className={styles.sIcon}>
            <FlatIcon name="tasks" size={22} tone="indigo" />
          </span>
          <p>
            <small>{t("summary.proposed")}</small>
            <b>{reviews.length}</b>
          </p>
        </div>
        <div>
          <span className={styles.sIcon}>
            <FlatIcon name="check" size={22} tone="green" />
          </span>
          <p>
            <small>{t("summary.accepted")}</small>
            <b>{accepted}</b>
          </p>
        </div>
        <div>
          <span className={styles.sIcon}>
            <FlatIcon name="clock" size={22} tone="amber" />
          </span>
          <p>
            <small>{t("summary.pending")}</small>
            <b>{pending}</b>
          </p>
        </div>
        <div className={styles.actions}>
          <button className={styles.btnSec} onClick={onReset} type="button">
            <X aria-hidden="true" size={14} /> {t("reset")}
          </button>
          <button
            className={styles.btnSec}
            disabled={pending === 0 || busy}
            onClick={() => onChange(reviews.map((r) => (r.status === "pending" ? { ...r, status: "accepted" } : r)))}
            type="button"
          >
            <CheckCircle2 aria-hidden="true" size={14} /> {t("acceptPending")}
          </button>
          <button className={styles.btn} disabled={pending !== 0 || accepted === 0 || busy} onClick={onCreate} type="button">
            <Send aria-hidden="true" size={14} /> {t("addToTasks")}
          </button>
        </div>
      </div>

      <div className={styles.roadCard}>
        <header className={styles.roadHead}>
          <span className={styles.dayIcon}>
            <FlatIcon name="flag" size={24} tone="red" />
          </span>
          <div>
            <h2>{dayTitle}</h2>
            <small>{t("roadSub", { count: reviews.length })}</small>
          </div>
        </header>
        {reviews.length === 0 ? (
          <p className={styles.empty}>{t("empty")}</p>
        ) : (
          <JourneyRoad
            actionsFor={(item) => {
              const review = reviews.find((r) => r.key === item.id);
              return [
                {
                  icon: <Check aria-hidden="true" size={12} />,
                  title: t("actions.accept"),
                  tone: "success" as const,
                  disabled: !review || review.status !== "pending",
                  onClick: () => setStatus(item.id, "accepted"),
                },
                { icon: <Eye aria-hidden="true" size={12} />, title: t("actions.source"), onClick: () => setDialog({ kind: "source", key: item.id }) },
                { icon: <Pencil aria-hidden="true" size={12} />, title: t("actions.edit"), onClick: () => setDialog({ kind: "edit", key: item.id }) },
                { icon: <Copy aria-hidden="true" size={12} />, title: t("actions.duplicate"), onClick: () => duplicate(item.id) },
                {
                  icon: <Trash2 aria-hidden="true" size={12} />,
                  title: t("actions.remove"),
                  tone: "danger" as const,
                  onClick: () => setDialog({ kind: "remove", key: item.id }),
                },
              ];
            }}
            items={items}
            labels={{ start: t("road.start"), finish: t("road.finish"), taskNo: (n) => t("road.taskNo", { n }) }}
            onOpen={(item) => setDialog({ kind: "source", key: item.id })}
          />
        )}
      </div>

      {dialog?.kind === "source" && current ? (
        <PortalModal
          closeLabel={tm("stage.close")}
          footer={
            <button className={m.btnSec} onClick={() => setDialog(null)} type="button">
              {tm("stage.close")}
            </button>
          }
          icon={Eye}
          onClose={() => setDialog(null)}
          subtitle={current.proposal.summary}
          title={current.proposal.title}
          tone="indigo"
          wide
        >
          <p className={styles.srcLabel}>{t("sources")}</p>
          {current.origin ? (
            <TaskSources sources={sourcesOf(current)} />
          ) : (
            <ul className={styles.sources}>
              {current.proposal.source_chunks.map((chunk, index) => (
                <li key={`${chunk.document_section_id}-${index}`}>“{chunk.quote}”</li>
              ))}
            </ul>
          )}
          {current.proposal.review_notes && current.proposal.review_notes.length > 0 ? (
            <>
              <p className={styles.srcLabel}>{t("reviewNotes")}</p>
              <ul className={styles.sources}>
                {current.proposal.review_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </>
          ) : null}
          {current.proposal.prerequisites && current.proposal.prerequisites.length > 0 ? (
            <>
              <p className={styles.srcLabel}>{t("prerequisites")}</p>
              <ul className={styles.sources}>
                {current.proposal.prerequisites.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </>
          ) : null}
          {current.proposal.instructions_markdown ? (
            <>
              <p className={styles.srcLabel}>{t("edit.steps")}</p>
              <pre className={styles.steps}>{current.proposal.instructions_markdown}</pre>
            </>
          ) : null}
        </PortalModal>
      ) : null}

      {dialog?.kind === "edit" && current ? (
        <EditDialog
          onClose={() => setDialog(null)}
          onSave={(proposal) => {
            onChange(
              reviews.map((r) =>
                r.key === current.key ? { ...r, proposal, status: r.status === "pending" ? "edited" : r.status } : r,
              ),
            );
            setDialog(null);
          }}
          proposal={current.proposal}
        />
      ) : null}

      {dialog?.kind === "remove" && current ? (
        <ConfirmModal
          body={t("remove.body", { title: current.proposal.title })}
          cancelLabel={tm("stage.cancel")}
          closeLabel={tm("stage.close")}
          confirmIcon={Trash2}
          confirmLabel={t("remove.confirm")}
          danger
          icon={Trash2}
          onCancel={() => setDialog(null)}
          onConfirm={() => {
            onChange(reviews.filter((r) => r.key !== current.key));
            setDialog(null);
          }}
          title={t("remove.title")}
        />
      ) : null}
    </section>
  );
}

function EditDialog({
  proposal,
  onClose,
  onSave,
}: {
  proposal: AiTaskProposalResponseDTO;
  onClose: () => void;
  onSave: (next: AiTaskProposalResponseDTO) => void;
}) {
  const t = useTranslations("portalHr.propose");
  const tm = useTranslations("portalHr");
  const [title, setTitle] = useState(proposal.title);
  const [summary, setSummary] = useState(proposal.summary);
  const [minutes, setMinutes] = useState(String(proposal.estimated_minutes ?? ""));
  const [steps, setSteps] = useState(proposal.instructions_markdown);
  const [done, setDone] = useState(proposal.done_criteria.join("\n"));

  function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseInt(minutes, 10);
    onSave({
      ...proposal,
      title: title.trim() || proposal.title,
      summary: summary.trim(),
      estimated_minutes: Number.isFinite(parsed) && parsed > 0 ? parsed : null,
      instructions_markdown: steps.trim(),
      done_criteria: done
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
    });
  }

  return (
    <PortalModal
      closeLabel={tm("stage.close")}
      footer={
        <>
          <button className={m.btnSec} onClick={onClose} type="button">
            {tm("stage.cancel")}
          </button>
          <button className={m.btn} form="ai-edit-form" type="submit">
            <Check aria-hidden="true" size={14} /> {t("edit.save")}
          </button>
        </>
      }
      icon={Pencil}
      onClose={onClose}
      title={t("edit.title")}
      tone="indigo"
      wide
    >
      <form id="ai-edit-form" onSubmit={submit}>
        <div className={m.fgrid}>
          <div className={m.span2}>
            <label htmlFor="ai-e-title">{t("edit.name")}</label>
            <input id="ai-e-title" onChange={(e) => setTitle(e.target.value)} required type="text" value={title} />
          </div>
          <div className={m.span2}>
            <label htmlFor="ai-e-summary">{t("edit.summary")}</label>
            <textarea id="ai-e-summary" onChange={(e) => setSummary(e.target.value)} value={summary} />
          </div>
          <div>
            <label htmlFor="ai-e-min">{t("edit.minutes")}</label>
            <input id="ai-e-min" inputMode="numeric" onChange={(e) => setMinutes(e.target.value)} type="text" value={minutes} />
          </div>
          <div className={m.span2}>
            <label htmlFor="ai-e-steps">{t("edit.steps")}</label>
            <textarea id="ai-e-steps" onChange={(e) => setSteps(e.target.value)} style={{ minHeight: 120 }} value={steps} />
          </div>
          <div className={m.span2}>
            <label htmlFor="ai-e-done">{t("edit.done")}</label>
            <textarea id="ai-e-done" onChange={(e) => setDone(e.target.value)} value={done} />
          </div>
        </div>
      </form>
    </PortalModal>
  );
}
