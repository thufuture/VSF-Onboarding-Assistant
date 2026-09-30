"use client";

import { History } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { PersonAvatar } from "@/components/avatar/PersonAvatar";
import { portalAdminApi } from "@/features/portal-admin/api";
import type { AdminAuditLogResponseDTO } from "@/features/portal-admin/dto/responseDTO/admin.response";

import { adminErrorMessage, adminStyles as s, formatDateTime, IconChip, PageHead, Pager, paginate } from "./adminUi";
import { auditIcon, auditTone } from "./auditMeta";

const PAGE_SIZE = 7;

/** "Nhật ký thay đổi" (v15 `viewAAudit`): ai đã làm gì, khi nào — đọc từ `audit_logs` thật. */
export function AdminAuditPage() {
  const t = useTranslations("portalAdmin");
  const [logs, setLogs] = useState<AdminAuditLogResponseDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    portalAdminApi
      .listAuditLogs()
      .then(setLogs)
      .catch((caught: unknown) => setError(adminErrorMessage(t, caught)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { rows, page: current } = paginate(logs ?? [], page, PAGE_SIZE);

  return (
    <div className={s.page}>
      <PageHead description={t("audit.description")} icon={History} title={t("audit.title")} tone="Slate" />
      {error ? <p className={s.banner}>{error}</p> : null}
      <div className={s.card}>
        <div className={s.tableWrap} style={{ minHeight: PAGE_SIZE * 47 + 41 }}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>{t("audit.table.time")}</th>
                <th>{t("audit.table.actor")}</th>
                <th>{t("audit.table.action")}</th>
                <th>{t("audit.table.target")}</th>
              </tr>
            </thead>
            <tbody>
              {logs === null ? (
                <tr>
                  <td className={s.emptyCell} colSpan={4}>
                    {t("common.loading")}
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td className={s.emptyCell} colSpan={4}>
                    {t("audit.empty")}
                  </td>
                </tr>
              ) : (
                rows.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: "nowrap" }}>{formatDateTime(log.created_at)}</td>
                    <td>
                      {log.actor_name ? (
                        <div className={s.cellrow}>
                          <PersonAvatar name={log.actor_name} sizePx={26} />
                          <span>{log.actor_name}</span>
                        </div>
                      ) : (
                        <span className={s.faint}>{t("audit.system")}</span>
                      )}
                    </td>
                    <td>
                      <div className={s.cellrow}>
                        <IconChip icon={auditIcon(log.action)} size={13} tone={auditTone(log.action)} />
                        <span>{t.has(`audit.actions.${log.action}`) ? t(`audit.actions.${log.action}`) : log.action}</span>
                      </div>
                    </td>
                    <td>
                      {log.target ??
                        `${t.has(`audit.entities.${log.entity_type}`) ? t(`audit.entities.${log.entity_type}`) : log.entity_type} #${log.entity_id}`}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <Pager
          label={t("common.count", { count: logs?.length ?? 0 })}
          onPage={setPage}
          page={current}
          pageSize={PAGE_SIZE}
          total={logs?.length ?? 0}
        />
      </div>
    </div>
  );
}
