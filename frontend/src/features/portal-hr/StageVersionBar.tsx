"use client";

import { Check, CheckCircle2, ChevronDown, GitBranchPlus, Trash2, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import type { VersionNodeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./StageVersionBar.module.scss";

type Props = {
  versions: VersionNodeResponseDTO[];
  selectedId: number | null;
  busy: boolean;
  onSelect: (versionId: number) => void;
  onCreateDraft: () => void;
  onApply: (version: VersionNodeResponseDTO) => void;
  onDelete: (version: VersionNodeResponseDTO) => void;
  onRollout: (version: VersionNodeResponseDTO) => void;
};

/**
 * Một hàng gọn nằm ngay dưới tên ngày: danh sách thả các phiên bản của ngày (không trải hết ra) và thao tác của bản đang
 * chọn. Một bản đang áp dụng (người tạo lộ trình mới nhận bản này), các bản nháp (chỉ nháp sửa được) và bản lưu trữ.
 * Áp dụng một bản nháp KHÔNG đổi lộ trình nhân viên đã có; họ nhận thông báo để tự cập nhật.
 */
export function StageVersionBar({ versions, selectedId, busy, onSelect, onCreateDraft, onApply, onDelete, onRollout }: Props) {
  const t = useTranslations("portalTasks.versions");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = versions.find((version) => version.id === selectedId) ?? null;
  const ordered = [...versions].sort((a, b) => b.version_no - a.version_no);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={styles.bar} data-testid="stage-version-bar">
      <div className={styles.picker} ref={ref}>
        <button
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-label={t("label")}
          className={`${styles.trigger} ${open ? styles.triggerOpen : ""}`}
          onClick={() => setOpen((value) => !value)}
          title={selected ? t(`hint.${selected.status}`) : undefined}
          type="button"
        >
          {selected ? (
            <>
              <b>{t("name", { n: selected.version_no })}</b>
              <span className={`${styles.pill} ${styles[`pill_${selected.status}`]}`}>{t(`status.${selected.status}`)}</span>
            </>
          ) : null}
          <ChevronDown aria-hidden="true" className={styles.chev} size={14} />
        </button>

        {open ? (
          <ul aria-label={t("label")} className={styles.menu} role="listbox">
            {ordered.map((version) => (
              <li key={version.id}>
                <button
                  aria-selected={version.id === selectedId}
                  className={`${styles.option} ${version.id === selectedId ? styles.optionOn : ""}`}
                  onClick={() => {
                    onSelect(version.id);
                    setOpen(false);
                  }}
                  role="option"
                  type="button"
                >
                  <span className={styles.optionText}>
                    <b>{t("name", { n: version.version_no })}</b>
                    <small>{t("taskCount", { count: version.tasks.length })}</small>
                  </span>
                  <span className={`${styles.pill} ${styles[`pill_${version.status}`]}`}>{t(`status.${version.status}`)}</span>
                  {version.id === selectedId ? <Check aria-hidden="true" className={styles.tick} size={14} /> : null}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <span aria-hidden="true" className={styles.divider} />

      <div className={styles.actions}>
        <button className={styles.btnSecSm} disabled={busy || !selected} onClick={onCreateDraft} type="button">
          <GitBranchPlus aria-hidden="true" size={13} /> {t("createDraft")}
        </button>
        {selected?.status === "DRAFT" ? (
          <>
            <button className={styles.btnPrimarySm} disabled={busy} onClick={() => onApply(selected)} type="button">
              <CheckCircle2 aria-hidden="true" size={13} /> {t("apply")}
            </button>
            <button className={styles.btnSecSm} disabled={busy} onClick={() => onDelete(selected)} type="button">
              <Trash2 aria-hidden="true" size={13} /> {t("deleteDraft")}
            </button>
          </>
        ) : null}
        {selected && selected.status !== "DRAFT" ? (
          <button className={styles.btnSecSm} onClick={() => onRollout(selected)} type="button">
            <Users aria-hidden="true" size={13} /> {t("rollout")}
          </button>
        ) : null}
      </div>
    </div>
  );
}
