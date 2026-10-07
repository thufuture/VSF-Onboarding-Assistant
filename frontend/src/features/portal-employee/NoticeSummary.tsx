"use client";

import { useTranslations } from "next-intl";

import type { JourneyNoticeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./NoticeSummary.module.scss";
import { summarizeNotice } from "./changeModel";

const LISTED = 8;

function Group({ title, items }: { title: string; items: string[] }) {
  const t = useTranslations("employee.changes.summary");
  if (items.length === 0) return null;
  return (
    <div className={styles.group}>
      <b>{title}</b>
      <ul>
        {items.slice(0, LISTED).map((item) => (
          <li key={item}>{item}</li>
        ))}
        {items.length > LISTED ? <li className={styles.more}>{t("more", { count: items.length - LISTED })}</li> : null}
      </ul>
    </div>
  );
}

/**
 * Một thông báo gói gọn "đã đổi gì" thành các nhóm: việc đã tự thêm, đã tự bỏ, được giữ vì đã làm xong, và việc bị sửa cần bạn xem.
 * Dùng cả trong hộp thoại mở từ chuông và trên trang "Lộ trình có chỉnh sửa".
 */
export function NoticeSummary({ notice }: { notice: JourneyNoticeResponseDTO }) {
  const t = useTranslations("employee.changes.summary");
  const summary = summarizeNotice(notice.changes);
  return (
    <div className={styles.summary}>
      {notice.new_stage ? <p className={styles.lead}>{t("newStage", { stage: notice.stage_title, count: summary.added.length })}</p> : null}
      <Group items={summary.added} title={t("added", { count: summary.added.length })} />
      <Group items={summary.removed} title={t("removed", { count: summary.removed.length })} />
      <Group items={summary.keptDone} title={t("keptDone", { count: summary.keptDone.length })} />
      <Group items={summary.review} title={t("review", { count: summary.review.length })} />
      {summary.added.length + summary.removed.length > 0 && !notice.new_stage ? (
        <p className={styles.note}>{t("autoNote")}</p>
      ) : null}
    </div>
  );
}
