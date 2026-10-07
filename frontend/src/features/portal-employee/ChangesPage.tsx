"use client";

import { useTranslations } from "next-intl";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { useSession } from "@/features/auth/SessionProvider";

import { ChangeCard } from "./ChangeCard";
import { isAutoApplied, isPending } from "./changeModel";
import shared from "./employee.module.scss";
import { useJourney } from "./JourneyProvider";
import { NoticeSummary } from "./NoticeSummary";
import { PageHero } from "./PageHero";

/**
 * "Lộ trình có chỉnh sửa": mỗi lần HR áp dụng một bản mới của một ngày, lộ trình của bạn KHÔNG tự đổi; việc đổi nằm ở đây
 * để bạn tự bấm "Cập nhật" (thay bằng nội dung mới nhất, giữ trạng thái) hoặc "Giữ bản cũ".
 */
export function EmployeeChangesPage() {
  const t = useTranslations("employee.changes");
  const { user } = useSession();
  const { notices, busyChangeId, previewChange, acceptChange, dismissChange, acceptAll, pendingCount } = useJourney();

  // Thông báo còn việc cần xử lý lên đầu; thông báo đã xử lý xong vẫn giữ để xem lại.
  const sorted = [...notices].sort((a, b) => {
    const pa = a.changes.some(isPending) ? 1 : 0;
    const pb = b.changes.some(isPending) ? 1 : 0;
    return pb - pa || b.created_at.localeCompare(a.created_at);
  });

  return (
    <>
      <PageHero
        avatarName={user.display_name}
        compact
        subtitle={pendingCount > 0 ? t("subtitlePending", { count: pendingCount }) : t("subtitleNone")}
        title={t("title")}
      />
      <div className={shared.container}>
        {sorted.length === 0 ? (
          <div className={`${shared.card} ${shared.empty}`}>
            <FlatIcon name="check" size={36} tone="green" />
            <b>{t("emptyTitle")}</b>
            <span>{t("emptyBody")}</span>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 18 }}>
            {sorted.map((notice) => {
              const pending = notice.changes.filter(isPending);
              return (
                <section key={notice.id} style={{ display: "grid", gap: 10 }}>
                  <div className={shared.cardHead} style={{ padding: "0 2px", border: 0 }}>
                    <h2>
                      {notice.new_stage
                        ? t("newStageTitle", { stage: notice.stage_title })
                        : t("noticeTitle", { stage: notice.stage_title, version: notice.version_no })}
                    </h2>
                    {pending.length > 1 ? (
                      <button
                        className={shared.btn}
                        disabled={busyChangeId !== null}
                        onClick={() => void acceptAll(notice.id)}
                        type="button"
                      >
                        {t("acceptAll", { count: pending.length })}
                      </button>
                    ) : null}
                  </div>
                  <div className={shared.card} style={{ padding: 16 }}>
                    <NoticeSummary notice={notice} />
                  </div>
                  {notice.changes
                    .filter((change) => !isAutoApplied(change) && !change.informational)
                    .map((change) => (
                    <ChangeCard
                      busy={busyChangeId === change.id || busyChangeId === -notice.id}
                      change={change}
                      key={change.id}
                      onAccept={(id) => void acceptChange(id)}
                      onDismiss={(id) => void dismissChange(id)}
                      previewChange={previewChange}
                    />
                  ))}
                </section>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
