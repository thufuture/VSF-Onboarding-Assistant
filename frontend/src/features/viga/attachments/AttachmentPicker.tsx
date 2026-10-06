"use client";

import { AlertTriangle, Film, Loader2, Paperclip, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef } from "react";

import styles from "./Attachments.module.scss";
import { ACCEPT, MAX_ATTACHMENTS, type useAttachments } from "./useAttachments";

/** Nút "Đính kèm ảnh/video" và hàng ảnh thu nhỏ có trạng thái tải, lỗi, nút bỏ từng tệp. */
export function AttachmentPicker({
  attachments,
  compact = false,
}: {
  attachments: ReturnType<typeof useAttachments>;
  /** Dạng ô soạn tin nhắn: chỉ một nút kẹp giấy tròn (lời nhắc nằm ở tooltip), ảnh thu nhỏ xếp thành hàng riêng phía trên. */
  compact?: boolean;
}) {
  const t = useTranslations("attachments");
  const input = useRef<HTMLInputElement>(null);
  const { items, add, remove, full } = attachments;

  return (
    <div className={compact ? styles.pickerCompact : styles.picker}>
      <div className={styles.bar}>
        {compact ? (
          <button
            aria-label={t("add")}
            className={styles.clip}
            disabled={full}
            onClick={() => input.current?.click()}
            title={`${t("add")}. ${t("hint", { max: MAX_ATTACHMENTS })}`}
            type="button"
          >
            <Paperclip aria-hidden="true" size={18} />
          </button>
        ) : (
          <>
            <button className={styles.add} disabled={full} onClick={() => input.current?.click()} type="button">
              <Paperclip aria-hidden="true" size={14} /> {t("add")}
            </button>
            <small>{t("hint", { max: MAX_ATTACHMENTS })}</small>
          </>
        )}
        <input
          accept={ACCEPT}
          aria-label={t("pick")}
          hidden
          multiple
          onChange={(event) => {
            add(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
          ref={input}
          type="file"
        />
      </div>
      {items.length > 0 ? (
        <ul className={styles.thumbs}>
          {items.map((item) => (
            <li className={styles.thumb} data-status={item.status} key={item.localId} title={item.name}>
              {item.preview ? (
                // eslint-disable-next-line @next/next/no-img-element -- xem thử cục bộ từ blob, không qua trình tối ưu ảnh
                <img alt={item.name} src={item.preview} />
              ) : (
                <span className={styles.file}>
                  <Film aria-hidden="true" size={22} />
                  <small>{item.name}</small>
                </span>
              )}
              {item.status === "uploading" ? (
                <span aria-label={t("uploading")} className={styles.overlay} role="status">
                  <Loader2 aria-hidden="true" className={styles.spin} size={18} />
                </span>
              ) : null}
              {item.status === "error" ? (
                <span className={`${styles.overlay} ${styles.bad}`} role="alert">
                  <AlertTriangle aria-hidden="true" size={16} />
                  <small>{t(`errors.${item.errorKey ?? "failed"}`)}</small>
                </span>
              ) : null}
              <button
                aria-label={t("remove", { name: item.name })}
                className={styles.remove}
                onClick={() => remove(item.localId)}
                type="button"
              >
                <X aria-hidden="true" size={12} />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
