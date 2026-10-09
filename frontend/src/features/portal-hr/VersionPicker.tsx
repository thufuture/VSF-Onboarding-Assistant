"use client";

import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { DocumentVersionResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import modalStyles from "./DocumentVersionsModal.module.scss";
import styles from "./StageVersionBar.module.scss";

/** Danh sách thả chọn phiên bản (cùng kiểu với chọn phiên bản của ngày ở trang Quản lý task), thay cho cột danh sách chiếm chỗ. */
export function VersionPicker({
  versions,
  selectedId,
  onSelect,
  label,
  stateLabel,
  effectiveLabel,
}: {
  versions: DocumentVersionResponseDTO[];
  selectedId: number | null;
  onSelect: (versionId: number) => void;
  label: string;
  stateLabel: (version: DocumentVersionResponseDTO) => string;
  effectiveLabel: (version: DocumentVersionResponseDTO) => string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = versions.find((version) => version.id === selectedId) ?? null;

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
    <div className={styles.picker} ref={ref}>
      <button
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={label}
        className={`${styles.trigger} ${open ? styles.triggerOpen : ""}`}
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        {selected ? (
          <>
            <b>{selected.version_label}</b>
            <i className={modalStyles.chip} data-state={selected.state}>
              {stateLabel(selected)}
            </i>
          </>
        ) : null}
        <ChevronDown aria-hidden="true" className={styles.chev} size={14} />
      </button>

      {open ? (
        <ul aria-label={label} className={styles.menu} role="listbox">
          {versions.map((version) => (
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
                  <b>{version.version_label}</b>
                  <small>{effectiveLabel(version)}</small>
                </span>
                <i className={modalStyles.chip} data-state={version.state}>
                  {stateLabel(version)}
                </i>
                {version.id === selectedId ? <Check aria-hidden="true" className={styles.tick} size={14} /> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
