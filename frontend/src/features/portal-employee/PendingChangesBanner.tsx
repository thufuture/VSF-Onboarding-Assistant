"use client";

import { PencilLine } from "lucide-react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

import { useJourney } from "./JourneyProvider";
import shared from "./employee.module.scss";

/** Nhắc ở đầu trang khi HR đã áp dụng bản mới và còn việc nhân viên chưa quyết định cập nhật hay giữ bản cũ. */
export function PendingChangesBanner() {
  const t = useTranslations("employee.changes");
  const { pendingCount } = useJourney();
  if (pendingCount === 0) return null;
  return (
    <div className={shared.changeBanner} data-testid="pending-changes-banner">
      <PencilLine aria-hidden="true" size={16} />
      <span>{t("banner", { count: pendingCount })}</span>
      <Link className={shared.btnGhost} href="/me/changes">
        {t("bannerLink")}
      </Link>
    </div>
  );
}
