"use client";

import { useTranslations } from "next-intl";

import type { TicketAttachmentResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

import styles from "./Attachments.module.scss";

/** Ảnh và video đã đính kèm một tin nhắn: ảnh bấm để mở bản đầy đủ, video xem ngay trong khung. */
export function AttachmentList({ attachments }: { attachments: TicketAttachmentResponseDTO[] }) {
  const t = useTranslations("attachments");
  if (attachments.length === 0) return null;
  return (
    <ul aria-label={t("listLabel")} className={styles.gallery}>
      {attachments.map((item) => (
        <li key={item.id}>
          {item.kind === "VIDEO" ? (
            <video aria-label={item.filename} controls preload="metadata" src={item.url} />
          ) : (
            <a href={item.url} rel="noopener noreferrer" target="_blank" title={item.filename}>
              {/* eslint-disable-next-line @next/next/no-img-element -- ảnh ngoài (Cloudinary) với kích thước chưa biết */}
              <img alt={item.filename} loading="lazy" src={item.url} />
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
