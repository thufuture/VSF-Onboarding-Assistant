"use client";

import { CheckCircle2, FilePlus2, RefreshCw, Search, SearchX, ThumbsDown, ThumbsUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { FlatIcon, type FlatIconName, type FlatTone } from "@/components/flat-icons/FlatIcon";
import { foldText } from "@/components/text/foldText";

import { vigaApi } from "./api";
import type {
  ContentGapResponseDTO,
  DissatisfiedGroupResponseDTO,
  RecheckGapResponseDTO,
  SatisfactionSummaryResponseDTO,
} from "./dto/responseDTO/viga.response";
import { SupplementModal } from "./SupplementModal";
import styles from "./VigaFeedbackPage.module.scss";

type RowKind = "NO_BASIS" | "PARTIAL" | "DOWN";
type Row = {
  key: string;
  kind: RowKind;
  id: number;
  question: string;
  count: number;
  last: string;
  resolved: boolean;
  excerpt: string | null;
  reasons: string[];
  comments: string[];
  resolvedDocument: string | null;
};

const KIND_VISUAL: Record<RowKind, { icon: FlatIconName; tone: FlatTone }> = {
  NO_BASIS: { icon: "alert", tone: "amber" },
  PARTIAL: { icon: "book", tone: "indigo" },
  DOWN: { icon: "chat", tone: "rose" },
};

function fromGap(gap: ContentGapResponseDTO): Row {
  return {
    key: `gap-${gap.id}`,
    kind: gap.kind === "PARTIAL" ? "PARTIAL" : "NO_BASIS",
    id: gap.id,
    question: gap.question_text,
    count: gap.occurrences,
    last: gap.last_asked_at,
    resolved: gap.resolved,
    excerpt: gap.answer_excerpt ?? null,
    reasons: [],
    comments: [],
    resolvedDocument: gap.resolved_document_title ?? null,
  };
}

function fromDown(group: DissatisfiedGroupResponseDTO): Row {
  return {
    key: `down-${group.id}`,
    kind: "DOWN",
    id: group.id,
    question: group.question_text,
    count: group.occurrences,
    last: group.last_at,
    resolved: group.resolved,
    excerpt: group.answer_excerpt || null,
    reasons: group.reasons,
    comments: group.comments,
    resolvedDocument: null,
  };
}

/**
 * "Phản hồi Viga": những câu Viga chưa trả lời được (không có căn cứ, hoặc chỉ trả lời một phần) và những câu nhân viên bấm 👎,
 * **ẩn danh** và chỉ của phòng ban mình. HR tìm, lọc, sắp xếp; "Bổ sung tài liệu" mở hộp viết đáp án ngay trên câu hỏi, rồi tự hỏi
 * lại Viga để biết đã đủ chưa. Chỉ khi Viga trả lời được thì câu mới tự đóng.
 */
export function VigaFeedbackPage() {
  const t = useTranslations("viga.feedback");
  const [gaps, setGaps] = useState<ContentGapResponseDTO[] | null>(null);
  const [downs, setDowns] = useState<DissatisfiedGroupResponseDTO[] | null>(null);
  const [summary, setSummary] = useState<SatisfactionSummaryResponseDTO | null>(null);
  const [failed, setFailed] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<RowKind | "ALL">("ALL");
  const [status, setStatus] = useState<"open" | "resolved" | "all">("open");
  const [sort, setSort] = useState<"count" | "recent">("count");

  const [supplementFor, setSupplementFor] = useState<Row | null>(null);
  const [rechecks, setRechecks] = useState<Record<string, RecheckGapResponseDTO | "running" | "failed">>({});

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([vigaApi.listContentGaps(true), vigaApi.listDissatisfied(true), vigaApi.feedbackSummary()])
      .then(([gapRows, downRows, stats]) => {
        if (cancelled) return;
        setGaps(gapRows);
        setDowns(downRows);
        setSummary(stats);
        setFailed(false);
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        setGaps((current) => current ?? []);
        setDowns((current) => current ?? []);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const rows = useMemo(() => [...(gaps ?? []).map(fromGap), ...(downs ?? []).map(fromDown)], [gaps, downs]);
  const loaded = gaps !== null && downs !== null;

  const counts = useMemo(() => {
    const open = rows.filter((row) => !row.resolved);
    return {
      NO_BASIS: open.filter((row) => row.kind === "NO_BASIS").length,
      PARTIAL: open.filter((row) => row.kind === "PARTIAL").length,
      DOWN: open.filter((row) => row.kind === "DOWN").length,
    };
  }, [rows]);

  const needle = foldText(query.trim());
  const shown = rows
    .filter((row) => (kind === "ALL" ? true : row.kind === kind))
    .filter((row) => (status === "all" ? true : status === "open" ? !row.resolved : row.resolved))
    .filter((row) => !needle || foldText([row.question, row.excerpt ?? "", ...row.comments].join(" ")).includes(needle))
    .sort((a, b) =>
      sort === "count" ? b.count - a.count || b.last.localeCompare(a.last) : b.last.localeCompare(a.last),
    );

  async function resolve(row: Row) {
    setBusyKey(row.key);
    try {
      if (row.kind === "DOWN") await vigaApi.resolveDissatisfied(row.id);
      else await vigaApi.resolveContentGap(row.id);
      reload();
    } catch {
      setFailed(true);
    } finally {
      setBusyKey(null);
    }
  }

  async function recheck(row: Row) {
    setRechecks((current) => ({ ...current, [row.key]: "running" }));
    try {
      const result = await vigaApi.recheckContentGap(row.id);
      setRechecks((current) => ({ ...current, [row.key]: result }));
      if (result.answered) reload();
    } catch {
      setRechecks((current) => ({ ...current, [row.key]: "failed" }));
    }
  }

  const percent = summary?.satisfaction_percent;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <span className={styles.headIcon}>
          <FlatIcon name="mail" size={30} tone="amber" />
        </span>
        <div className={styles.headText}>
          <h1>{t("title")}</h1>
          <p>{t("description")}</p>
        </div>
        <dl className={styles.kpis}>
          <div className={styles.kpiGood}>
            <ThumbsUp aria-hidden="true" size={16} />
            <dd>{percent === null || percent === undefined ? "—" : `${percent}%`}</dd>
            <dt>{t("satisfaction")}</dt>
          </div>
          <div className={styles.kpiBad}>
            <ThumbsDown aria-hidden="true" size={16} />
            <dd>{counts.DOWN}</dd>
            <dt>{t("openDown")}</dt>
          </div>
          <div className={styles.kpiWarn}>
            <FlatIcon name="alert" size={18} tone="amber" />
            <dd>{counts.NO_BASIS + counts.PARTIAL}</dd>
            <dt>{t("openGaps")}</dt>
          </div>
        </dl>
      </header>

      <div className={styles.toolbar}>
        <label className={styles.search}>
          <Search aria-hidden="true" size={14} />
          <input
            aria-label={t("searchLabel")}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("searchPlaceholder")}
            type="search"
            value={query}
          />
        </label>
        <select aria-label={t("kindLabel")} onChange={(event) => setKind(event.target.value as RowKind | "ALL")} value={kind}>
          <option value="ALL">{t("kind.ALL")}</option>
          {(["NO_BASIS", "PARTIAL", "DOWN"] as const).map((key) => (
            <option key={key} value={key}>
              {t(`kind.${key}`)} ({counts[key]})
            </option>
          ))}
        </select>
        <select
          aria-label={t("statusLabel")}
          onChange={(event) => setStatus(event.target.value as "open" | "resolved" | "all")}
          value={status}
        >
          <option value="open">{t("status.open")}</option>
          <option value="resolved">{t("status.resolved")}</option>
          <option value="all">{t("status.all")}</option>
        </select>
        <select aria-label={t("sortLabel")} onChange={(event) => setSort(event.target.value as "count" | "recent")} value={sort}>
          <option value="count">{t("sort.count")}</option>
          <option value="recent">{t("sort.recent")}</option>
        </select>
      </div>

      {failed ? <p className={styles.error}>{t("error")}</p> : null}

      <div className={styles.card}>
        {!loaded ? (
          <p className={styles.faint}>{t("loading")}</p>
        ) : rows.length === 0 ? (
          <div className={styles.empty}>
            <FlatIcon name="check" size={52} tone="green" />
            <b>{t("emptyTitle")}</b>
            <small>{t("emptyHint")}</small>
          </div>
        ) : shown.length === 0 ? (
          <div className={styles.empty}>
            <SearchX aria-hidden="true" size={34} />
            <b>{t("noMatch")}</b>
            <small>{t("noMatchHint")}</small>
          </div>
        ) : (
          <ul className={styles.list}>
            {shown.map((row) => {
              const visual = row.resolved ? { icon: "check" as FlatIconName, tone: "green" as FlatTone } : KIND_VISUAL[row.kind];
              const check = rechecks[row.key];
              return (
                <li className={styles.row} data-kind={row.kind} data-resolved={row.resolved} key={row.key}>
                  <span className={styles.rowIcon}>
                    <FlatIcon name={visual.icon} size={26} tone={visual.tone} />
                  </span>
                  <div className={styles.rowBody}>
                    <div className={styles.rowTop}>
                      <b title={row.question}>{row.question}</b>
                      <i className={styles.kind} data-kind={row.kind}>
                        {t(`rowKind.${row.kind}`)}
                      </i>
                      <i className={styles.count}>{t("times", { count: row.count })}</i>
                      <small>{new Date(row.last).toLocaleDateString("vi-VN")}</small>
                    </div>

                    {row.excerpt ? (
                      <p className={styles.excerpt}>
                        <em>{t(row.kind === "DOWN" ? "answeredWas" : "partialAnswered")}</em> {row.excerpt}
                      </p>
                    ) : null}
                    {row.reasons.length > 0 || row.comments.length > 0 ? (
                      <div className={styles.reasons}>
                        {row.reasons.map((reason) => (
                          <i key={reason}>{t(`reasons.${reason}`)}</i>
                        ))}
                        {row.comments.map((comment) => (
                          <q key={comment}>{comment}</q>
                        ))}
                      </div>
                    ) : null}
                    {row.resolved && row.resolvedDocument ? (
                      <p className={styles.resolvedBy}>
                        <CheckCircle2 aria-hidden="true" size={13} /> {t("resolvedBy", { title: row.resolvedDocument })}
                      </p>
                    ) : null}

                    {check === "running" ? <p className={styles.checkNote}>{t("rechecking")}</p> : null}
                    {check === "failed" ? <p className={styles.checkFail}>{t("recheckError")}</p> : null}
                    {check && typeof check === "object" ? (
                      check.answered ? (
                        <div className={styles.checkOk}>
                          <b>
                            <CheckCircle2 aria-hidden="true" size={14} /> {t("recheckOk")}
                          </b>
                          <p>{check.message}</p>
                          {check.document_title ? (
                            <small>
                              {check.document_title}
                              {check.section_heading ? ` · ${check.section_heading}` : ""}
                            </small>
                          ) : null}
                        </div>
                      ) : (
                        <p className={styles.checkFail}>{t("recheckFail")}</p>
                      )
                    ) : null}
                  </div>

                  {row.resolved ? (
                    <span className={styles.done}>
                      <CheckCircle2 aria-hidden="true" size={14} /> {t("resolved")}
                    </span>
                  ) : (
                    <div className={styles.actions}>
                      {row.kind !== "DOWN" ? (
                        <>
                          <button className={styles.primary} onClick={() => setSupplementFor(row)} type="button">
                            <FilePlus2 aria-hidden="true" size={13} /> {t("addDocument")}
                          </button>
                          <button disabled={check === "running"} onClick={() => void recheck(row)} type="button">
                            <RefreshCw aria-hidden="true" size={13} /> {t("recheck")}
                          </button>
                        </>
                      ) : null}
                      <button disabled={busyKey === row.key} onClick={() => void resolve(row)} type="button">
                        <CheckCircle2 aria-hidden="true" size={13} /> {t("resolve")}
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <p className={styles.privacy}>{t("privacy")}</p>
      </div>

      {supplementFor ? (
        <SupplementModal
          gapId={supplementFor.id}
          onClose={() => setSupplementFor(null)}
          onResolved={reload}
          question={supplementFor.question}
        />
      ) : null}
    </div>
  );
}
