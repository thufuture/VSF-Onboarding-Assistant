"use client";

import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import type { DocumentCategoryResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./CategoryPicker.module.scss";
import { categoryFlat } from "./docCategory";

/**
 * Ô chọn nhóm tài liệu thay cho ô chọn gốc của trình duyệt: danh sách thả xuống có biểu tượng nhiều màu, tên và mô tả ngắn của từng
 * nhóm; mở bằng chuột hoặc bàn phím, đóng khi bấm ra ngoài hoặc nhấn Esc.
 */
export function CategoryPicker({
  id,
  value,
  options,
  hints,
  onChange,
}: {
  id: string;
  value: string;
  options: DocumentCategoryResponseDTO[];
  /** Mô tả ngắn theo mã nhóm; nhóm không có mô tả thì chỉ hiện tên. */
  hints: Record<string, string>;
  onChange: (slug: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement | null>(null);
  const current = options.find((option) => option.slug === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const visual = categoryFlat(current?.name ?? "");

  return (
    <div className={styles.picker} ref={root}>
      <button
        aria-expanded={open}
        aria-haspopup="listbox"
        className={styles.trigger}
        id={id}
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className={styles.icon}>
          <FlatIcon name={visual.icon} size={22} tone={visual.tone} />
        </span>
        <span className={styles.text}>
          <b>{current?.name ?? ""}</b>
          {current && hints[current.slug] ? <small>{hints[current.slug]}</small> : null}
        </span>
        <ChevronDown aria-hidden="true" className={open ? styles.caretOpen : ""} size={15} />
      </button>
      {open ? (
        <ul className={styles.menu} role="listbox">
          {options.map((option) => {
            const flat = categoryFlat(option.name);
            const selected = option.slug === current?.slug;
            return (
              <li aria-selected={selected} key={option.slug} role="option">
                <button
                  className={selected ? styles.on : ""}
                  onClick={() => {
                    onChange(option.slug);
                    setOpen(false);
                  }}
                  type="button"
                >
                  <span className={styles.icon}>
                    <FlatIcon name={flat.icon} size={22} tone={flat.tone} />
                  </span>
                  <span className={styles.text}>
                    <b>{option.name}</b>
                    {hints[option.slug] ? <small>{hints[option.slug]}</small> : null}
                  </span>
                  {selected ? <Check aria-hidden="true" size={15} /> : null}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
