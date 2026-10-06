"use client";

import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { useSession } from "@/features/auth/SessionProvider";
import { TicketBoard } from "@/features/viga/TicketBoard";

import shared from "./employee.module.scss";
import { PageHero } from "./PageHero";

/** "Yêu cầu của tôi": ticket đã gửi cho HR (từ nút "Gửi câu hỏi này cho HR" của Viga) và phản hồi của HR. */
export function EmployeeTicketsPage() {
  const t = useTranslations("employee.tickets");
  const { user } = useSession();
  const requested = Number(useSearchParams().get("ticket"));

  return (
    <>
      <PageHero avatarName={user.display_name} compact subtitle={t("subtitle")} title={t("title")} />
      <div className={shared.container}>
        <TicketBoard initialTicketId={Number.isInteger(requested) && requested > 0 ? requested : null} staff={false} />
      </div>
    </>
  );
}
