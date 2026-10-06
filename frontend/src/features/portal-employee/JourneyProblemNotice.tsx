"use client";

import { Route } from "lucide-react";
import { useTranslations } from "next-intl";

import { useJourney } from "./JourneyProvider";
import shared from "./employee.module.scss";

/**
 * Hiện khi chưa có lộ trình để xem. Lộ trình KHÔNG tự tạo và nhân viên cũng không tự tạo: chỉ HR thêm lộ trình cho nhân
 * viên (trang "Nhân viên" của HR). Các trường hợp còn lại chỉ là thông báo.
 */
export function JourneyProblemNotice() {
  const t = useTranslations("employee.journeyProblem");
  const { problem } = useJourney();
  if (!problem) return null;

  if (problem === "needsCreate") {
    return (
      <div className={`${shared.card} ${shared.empty}`} data-testid="no-journey">
        <Route aria-hidden="true" size={34} />
        <b>{t("needsCreateTitle")}</b>
        <span>{t("needsCreateBody")}</span>
      </div>
    );
  }
  return <p className={shared.banner}>{t(problem)}</p>;
}
