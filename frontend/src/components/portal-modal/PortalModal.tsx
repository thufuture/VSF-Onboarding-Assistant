"use client";

import { AlertTriangle, X, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import styles from "./PortalModal.module.scss";

type Tone = "blue" | "rose" | "indigo" | "teal" | "amber";

/** Khung modal cổng đúng .overlay/.modal/.mhead/.mtabs/.mbody/.mfoot của prototype v15. */
export function PortalModal({
  icon: Icon,
  tone = "blue",
  title,
  subtitle,
  wide = false,
  vwide = false,
  closeLabel,
  onClose,
  tabs,
  footer,
  children,
}: {
  icon: LucideIcon;
  tone?: Tone;
  title: string;
  subtitle?: string;
  wide?: boolean;
  vwide?: boolean;
  closeLabel: string;
  onClose: () => void;
  tabs?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className={styles.overlay} onClick={onClose} role="presentation">
      <div
        aria-modal="true"
        className={`${styles.modal} ${wide ? styles.wide : ""} ${vwide ? styles.vwide : ""}`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className={styles.mhead}>
          <span className={`${styles.ichip} ${styles[tone]}`}>
            <Icon aria-hidden="true" size={16} />
          </span>
          <div className={styles.mt}>
            <h2>{title}</h2>
            {subtitle ? <small>{subtitle}</small> : null}
          </div>
          <button aria-label={closeLabel} className={styles.ibtn} onClick={onClose} type="button">
            <X aria-hidden="true" size={16} />
          </button>
        </div>
        {tabs ? <div className={styles.mtabs}>{tabs}</div> : null}
        <div className={styles.mbody}>{children}</div>
        {footer ? <div className={styles.mfoot}>{footer}</div> : null}
      </div>
    </div>
  );
}

/** Hộp xác nhận (xóa/ẩn/kích hoạt lại/nhân bản...) — mọi hành động có tác dụng phụ đều đi qua đây. */
export function ConfirmModal({
  icon,
  tone = "rose",
  title,
  body,
  warning,
  confirmLabel,
  confirmIcon: ConfirmIcon,
  cancelLabel,
  closeLabel,
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  icon: LucideIcon;
  tone?: Tone;
  title: string;
  body?: string;
  warning?: string;
  confirmLabel: string;
  confirmIcon?: LucideIcon;
  cancelLabel: string;
  closeLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <PortalModal
      closeLabel={closeLabel}
      footer={
        <>
          <button className={styles.btnSec} onClick={onCancel} type="button">
            {cancelLabel}
          </button>
          <button
            className={danger ? styles.btnDanger : styles.btn}
            disabled={busy}
            onClick={onConfirm}
            type="button"
          >
            {ConfirmIcon ? <ConfirmIcon aria-hidden="true" size={14} /> : null} {confirmLabel}
          </button>
        </>
      }
      icon={icon}
      onClose={onCancel}
      title={title}
      tone={tone}
    >
      {body ? <p className={styles.confirmBody}>{body}</p> : null}
      {warning ? (
        <div className={styles.noteWarn}>
          <AlertTriangle aria-hidden="true" size={14} />
          <span>{warning}</span>
        </div>
      ) : null}
    </PortalModal>
  );
}

/** Thông báo nổi giữa đáy màn hình (.toast của v15), tự tắt sau 2,6 giây. */
export function useToast(): [ReactNode, (message: string) => void] {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<number | null>(null);
  const show = useCallback((next: string) => {
    setMessage(next);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setMessage(null), 2600);
  }, []);
  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );
  return [message ? <div className={styles.toast} key="toast" role="status">{message}</div> : null, show];
}

export const modalStyles = styles;
