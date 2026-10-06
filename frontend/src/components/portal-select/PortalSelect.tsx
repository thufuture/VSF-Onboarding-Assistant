"use client";

import { Check, ChevronDown } from "lucide-react";
import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";

import styles from "./PortalSelect.module.scss";

export type PortalSelectOption = {
  value: string;
  label: string;
  /** Màu chấm nhỏ đầu dòng (trạng thái); bỏ trống thì không có chấm. */
  tone?: "amber" | "blue" | "green" | "slate";
};

/**
 * Ô chọn có danh sách thả xuống tự vẽ (thẻ <select> gốc không tùy biến được phần danh sách): bo tròn, đổ bóng, tô dòng đang
 * chọn bằng dấu tick. Dùng bàn phím được (mũi tên, Enter, Esc, Home/End) và đóng khi bấm ra ngoài.
 */
export function PortalSelect({
  value,
  options,
  onChange,
  ariaLabel,
  pill = false,
  className,
}: {
  value: string;
  options: PortalSelectOption[];
  onChange: (value: string) => void;
  ariaLabel: string;
  /** Viên thuốc tô màu theo trạng thái (đầu khung của HR) thay vì ô viền mảnh. */
  pill?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const listId = useId();
  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );
  const selected = options[selectedIndex];

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  function toggle() {
    if (!open) setActive(selectedIndex);
    setOpen(!open);
  }

  function choose(index: number) {
    const option = options[index];
    if (option) onChange(option.value);
    setOpen(false);
  }

  function onKey(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Home" || event.key === "End") {
      event.preventDefault();
      if (!open) {
        setActive(selectedIndex);
        setOpen(true);
        return;
      }
      setActive((current) =>
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? options.length - 1
            : Math.min(options.length - 1, Math.max(0, current + (event.key === "ArrowDown" ? 1 : -1))),
      );
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && open) {
      event.preventDefault();
      choose(active);
    }
  }

  return (
    <div className={`${styles.root} ${className ?? ""}`} ref={root}>
      <button
        aria-controls={open ? listId : undefined}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        className={`${styles.trigger} ${pill ? styles.pill : ""}`}
        data-tone={selected?.tone}
        onClick={toggle}
        onKeyDown={onKey}
        role="combobox"
        type="button"
      >
        {selected?.tone ? <span className={styles.dot} data-tone={selected.tone} /> : null}
        <span className={styles.value}>{selected?.label}</span>
        <ChevronDown aria-hidden="true" className={open ? styles.open : ""} size={14} />
      </button>
      {open ? (
        <ul aria-label={ariaLabel} className={styles.menu} id={listId} role="listbox">
          {options.map((option, index) => (
            <li
              aria-selected={option.value === value}
              className={`${styles.option} ${index === active ? styles.active : ""} ${option.value === value ? styles.on : ""}`}
              key={option.value}
              onClick={() => choose(index)}
              onMouseEnter={() => setActive(index)}
              role="option"
            >
              {option.tone ? <span className={styles.dot} data-tone={option.tone} /> : null}
              <span className={styles.value}>{option.label}</span>
              {option.value === value ? <Check aria-hidden="true" size={14} /> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
