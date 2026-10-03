"use client";

import { Flag } from "lucide-react";
import { useTranslations } from "next-intl";

import { TicketBoard } from "./TicketBoard";
import styles from "./VigaPages.module.scss";

/** "Ticket sự cố" của HR: hàng đợi chung của phòng ban, một HR bấm "Nhận xử lý" thì mới gán; Admin thấy mọi phòng ban. */
export function HrTicketsPage() {
  const t = useTranslations("viga.hrTickets");
  return (
    <div className={styles.page}>
      <header className={styles.pagehead}>
        <span className={styles.phi}>
          <Flag aria-hidden="true" size={22} />
        </span>
        <div>
          <h1>{t("title")}</h1>
          <p>{t("description")}</p>
        </div>
      </header>
      <TicketBoard staff />
    </div>
  );
}
