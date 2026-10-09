"use client";

import { Equal, FilePen, FilePlus2, FileX2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { portalHrApi } from "@/features/portal-hr/api";
import type { SectionChangeDTO, VersionComparisonResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./VersionComparePanel.module.scss";

type Translate = (key: string, values?: Record<string, string | number>) => string;
type Filter = "changed" | "all";

/** Tab "So với bản trước": mục thêm, sửa, xóa, và từng từ đổi trong mục đã sửa (chỉ đọc; so chữ, không so định dạng Word). */
export function VersionComparePanel({ documentId, versionId }: { documentId: number; versionId: number }) {
  const t = useTranslations("portalDocuments.versions.compare") as unknown as Translate;
  const [result, setResult] = useState<{ id: number; data: VersionComparisonResponseDTO } | { id: number; failed: true } | null>(
    null,
  );
  const [filter, setFilter] = useState<Filter>("changed");

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .compareDocumentVersion(documentId, versionId)
      .then((data) => !cancelled && setResult({ id: versionId, data }))
      .catch(() => !cancelled && setResult({ id: versionId, failed: true }));
    return () => {
      cancelled = true;
    };
  }, [documentId, versionId]);

  if (result === null || result.id !== versionId) return <p className={styles.faint}>{t("loading")}</p>;
  if ("failed" in result) return <p className={styles.error}>{t("failed")}</p>;
  const data = result.data;
  if (!data.has_base) return <p className={styles.faint}>{t("noBase")}</p>;

  const changedCount = data.added + data.removed + data.modified;
  const shown = filter === "all" ? data.sections : data.sections.filter((s) => s.status !== "unchanged");

  const stats = [
    { status: "modified", count: data.modified, icon: FilePen },
    { status: "added", count: data.added, icon: FilePlus2 },
    { status: "removed", count: data.removed, icon: FileX2 },
    { status: "unchanged", count: data.unchanged, icon: Equal },
  ] as const;

  return (
    <div className={styles.panel}>
      <div className={styles.toolbar}>
        <b>{t("against", { label: data.base_version_label ?? "" })}</b>
        {changedCount === 0 ? <span className={styles.faint}>{t("noChange")}</span> : null}
        <div className={styles.stats}>
          {stats.map(({ status, count, icon: Icon }) => (
            <span className={styles.stat} data-status={status} key={status} title={t(`status.${status}`)}>
              <Icon aria-hidden="true" size={15} />
              <b>{count}</b>
              <small>{t(`status.${status}`)}</small>
            </span>
          ))}
        </div>
        <div className={styles.filters} role="group">
          {(["changed", "all"] as const).map((value) => (
            <button aria-pressed={filter === value} key={value} onClick={() => setFilter(value)} type="button">
              {t(`filter.${value}`)}
            </button>
          ))}
        </div>
      </div>
      {data.recompute && changedCount > 0 ? (
        <p className={styles.estimate}>
          {t("estimate", {
            embed: data.recompute.chunks_to_embed,
            total: data.recompute.chunks_total,
            seconds: data.recompute.estimated_seconds,
          })}
        </p>
      ) : null}
      <div className={styles.sides} aria-hidden="true">
        <span>
          <i className={styles.sign} data-sign="minus">−</i> {t("before")} · {data.base_version_label}
        </span>
        <span>
          <i className={styles.sign} data-sign="plus">+</i> {t("after")}
        </span>
      </div>
      <ul className={styles.list}>
        {shown.map((section, index) => (
          <SectionRow key={`${index}-${section.heading ?? ""}`} section={section} t={t} />
        ))}
      </ul>
    </div>
  );
}

type Seg = { op: "equal" | "insert" | "delete"; text: string; strong?: boolean };
type DiffLine = { segs: Seg[]; changed: boolean };

const MAX_CHAR_DIFF = 600;

/** So từng ký tự giữa cụm bị xóa và cụm thay vào: ký tự thật sự khác được đánh dấu `strong`, phần giống chỉ tô nhạt. */
function charDiff(removed: string, added: string): { oldParts: Seg[]; newParts: Seg[] } {
  const a = Array.from(removed);
  const b = Array.from(added);
  if (a.length > MAX_CHAR_DIFF || b.length > MAX_CHAR_DIFF) {
    return { oldParts: [{ op: "delete", text: removed, strong: true }], newParts: [{ op: "insert", text: added, strong: true }] };
  }
  // Bảng độ dài dãy con chung dài nhất, rồi lần ngược để biết ký tự nào giữ lại.
  const table: number[][] = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i -= 1)
    for (let j = b.length - 1; j >= 0; j -= 1)
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
  const oldParts: Seg[] = [];
  const newParts: Seg[] = [];
  const push = (list: Seg[], op: "delete" | "insert", ch: string, strong: boolean) => {
    const last = list[list.length - 1];
    if (last && last.strong === strong) last.text += ch;
    else list.push({ op, text: ch, strong });
  };
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      push(oldParts, "delete", a[i], false);
      push(newParts, "insert", b[j], false);
      i += 1;
      j += 1;
    } else if (j < b.length && (i === a.length || table[i][j + 1] >= table[i + 1][j])) {
      push(newParts, "insert", b[j], true);
      j += 1;
    } else {
      push(oldParts, "delete", a[i], true);
      i += 1;
    }
  }
  return { oldParts, newParts };
}

/** Tách các đoạn so sánh thành hai phía; cụm xóa kề cụm thêm thì so tiếp từng ký tự để chỉ rõ ký tự nào đổi. */
function splitSides(segments: Seg[]): { oldSegs: Seg[]; newSegs: Seg[] } {
  const oldSegs: Seg[] = [];
  const newSegs: Seg[] = [];
  for (let k = 0; k < segments.length; k += 1) {
    const seg = segments[k];
    const next = segments[k + 1];
    if (seg.op === "delete" && next?.op === "insert") {
      const { oldParts, newParts } = charDiff(seg.text, next.text);
      oldSegs.push(...oldParts);
      newSegs.push(...newParts);
      k += 1;
    } else if (seg.op === "delete") oldSegs.push({ ...seg, strong: true });
    else if (seg.op === "insert") newSegs.push({ ...seg, strong: true });
    else {
      oldSegs.push(seg);
      newSegs.push(seg);
    }
  }
  return { oldSegs, newSegs };
}

/** Tách các đoạn so sánh của MỘT phía thành từng dòng; dòng nào có từ thêm/xóa thì đánh dấu là dòng đã đổi. */
function toLines(items: Seg[]): DiffLine[] {
  const lines: DiffLine[] = [{ segs: [], changed: false }];
  for (const seg of items) {
    seg.text.split("\n").forEach((part, index) => {
      if (index > 0) lines.push({ segs: [], changed: false });
      const line = lines[lines.length - 1];
      if (part === "") return;
      line.segs.push({ ...seg, text: part });
      if (seg.op !== "equal") line.changed = true;
    });
  }
  // Bỏ dòng trống không đổi ở rìa và gộp các dòng trống liền nhau cho gọn.
  return lines.filter((line, i) => line.changed || line.segs.length > 0 || (i > 0 && i < lines.length - 1 && lines[i - 1].segs.length > 0));
}

/** Kiểu GitHub: hai cột cạnh nhau, mỗi dòng có dấu − (bản cũ, đỏ) hoặc + (bản này, xanh) ở lề; dòng không đổi để mờ làm ngữ cảnh. */
function SectionRow({ section, t }: { section: SectionChangeDTO; t: Translate }) {
  const title = section.heading ?? t("noHeading");
  const { oldSegs, newSegs } = splitSides(section.segments);
  const renamed = section.old_heading !== null;
  const oldLines = toLines(oldSegs);
  const newLines = toLines(newSegs);
  if (renamed) {
    // Tiêu đề mục đổi tên cũng là một thay đổi: hiện thành dòng đầu của mỗi cột.
    const { oldParts, newParts } = charDiff(section.old_heading ?? "", title);
    oldLines.unshift({ segs: oldParts, changed: true });
    newLines.unshift({ segs: newParts, changed: true });
  }
  const column = (lines: DiffLine[], side: "old" | "new") => (
    <div className={styles.pane} data-side={side} data-empty={lines.length === 0 ? "true" : undefined}>
      {lines.map((line, i) => (
        <div className={styles.line} data-changed={line.changed ? "true" : undefined} key={i}>
          <span aria-hidden="true" className={styles.gutter}>
            {line.changed ? (side === "old" ? "−" : "+") : ""}
          </span>
          <span className={styles.code}>
            {line.segs.map((seg, j) =>
              seg.op === "insert" ? (
                <ins data-strong={seg.strong ? "true" : undefined} key={j}>
                  {seg.text}
                </ins>
              ) : seg.op === "delete" ? (
                <del data-strong={seg.strong ? "true" : undefined} key={j}>
                  {seg.text}
                </del>
              ) : (
                <span key={j}>{seg.text}</span>
              ),
            )}
          </span>
        </div>
      ))}
    </div>
  );
  return (
    <li className={styles.item} data-status={section.status}>
      <div className={styles.itemHead}>
        <span className={styles.tag} data-status={section.status}>
          {t(`status.${section.status}`)}
        </span>
        <b>{title}</b>
        {section.status !== "unchanged" ? (
          <small className={styles.counts}>
            {section.added_words > 0 ? <span className={styles.plus}>+{section.added_words}</span> : null}
            {section.removed_words > 0 ? <span className={styles.minus}>−{section.removed_words}</span> : null}
          </small>
        ) : null}
      </div>
      {section.segments.length > 0 || renamed ? (
        <div className={styles.split}>
          {column(oldLines, "old")}
          {column(newLines, "new")}
        </div>
      ) : null}
    </li>
  );
}
