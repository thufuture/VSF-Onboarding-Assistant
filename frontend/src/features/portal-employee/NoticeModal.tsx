"use client";

import { PencilLine } from "lucide-react";
import { useTranslations } from "next-intl";
import { createPortal } from "react-dom";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import type { JourneyNoticeResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";
import { useRouter } from "@/i18n/navigation";

import { NoticeSummary } from "./NoticeSummary";

/** Hộp thoại mở từ chuông: thông báo này đã đổi gì trong lộ trình; "Xem chi tiết" mở trang chỉnh sửa. */
export function NoticeModal({ notice, onClose }: { notice: JourneyNoticeResponseDTO; onClose: () => void }) {
  const t = useTranslations("employee.changes");
  const router = useRouter();
  // Vẽ vào phần tử gốc của khung ứng dụng (như DocumentModal) để không bị thanh tiêu đề che và vẫn có bộ biến màu.
  const host = document.querySelector<HTMLElement>("[data-theme]") ?? document.body;
  return createPortal(
    <PortalModal
      closeLabel={t("close")}
      footer={
        <>
          <button className={m.btnSec} onClick={onClose} type="button">
            {t("close")}
          </button>
          <button
            className={m.btn}
            onClick={() => {
              onClose();
              router.push("/me/changes");
            }}
            type="button"
          >
            {t("detail")}
          </button>
        </>
      }
      icon={PencilLine}
      onClose={onClose}
      title={notice.new_stage ? t("modalNewStage", { stage: notice.stage_title }) : t("modalTitle", { stage: notice.stage_title })}
      tone="indigo"
    >
      <NoticeSummary notice={notice} />
    </PortalModal>,
    host,
  );
}
