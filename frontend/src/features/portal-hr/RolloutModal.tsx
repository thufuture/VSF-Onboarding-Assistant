"use client";

import { Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { modalStyles as m, PortalModal } from "@/components/portal-modal/PortalModal";
import { portalHrApi } from "@/features/portal-hr/api";
import type { RolloutRowResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import styles from "./RolloutModal.module.scss";

/** Theo dõi triển khai một phiên bản: mỗi nhân viên đã xem chưa, đã cập nhật hay giữ bản cũ (chỉ xem, HR không sửa hộ). */
export function RolloutModal({ versionId, versionNo, onClose }: { versionId: number; versionNo: number; onClose: () => void }) {
  const t = useTranslations("portalTasks.rollout");
  const tc = useTranslations("portalTasks");
  const [rows, setRows] = useState<RolloutRowResponseDTO[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .getVersionRollout(versionId)
      .then((result) => {
        if (!cancelled) setRows(result);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [versionId]);

  const count = (state: RolloutRowResponseDTO["state"]) => (rows ?? []).filter((row) => row.state === state).length;

  return (
    <PortalModal
      closeLabel={tc("close")}
      footer={
        <button className={m.btnSec} onClick={onClose} type="button">
          {tc("closeButton")}
        </button>
      }
      icon={Users}
      onClose={onClose}
      subtitle={t("subtitle")}
      title={t("title", { n: versionNo })}
      wide
    >
      {failed ? (
        <p className={m.faint}>{t("failed")}</p>
      ) : rows === null ? (
        <p className={m.faint}>{tc("loading")}</p>
      ) : rows.length === 0 ? (
        <p className={m.faint}>{t("empty")}</p>
      ) : (
        <>
          <p className={m.faint} data-testid="rollout-summary">
            {t("summary", {
              total: rows.length,
              unseen: count("UNSEEN"),
              seen: count("SEEN"),
              updated: count("UPDATED"),
              kept: count("KEPT_OLD"),
            })}
          </p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>{t("col.employee")}</th>
                <th>{t("col.state")}</th>
                <th>{t("col.pending")}</th>
                <th>{t("col.accepted")}</th>
                <th>{t("col.dismissed")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.notice_id}>
                  <td>
                    <b>{row.display_name}</b>
                    <small>{row.email}</small>
                  </td>
                  <td>
                    <span className={`${styles.state} ${styles[`state_${row.state}`]}`}>{t(`state.${row.state}`)}</span>
                  </td>
                  <td>{row.pending}</td>
                  <td>{row.accepted}</td>
                  <td>{row.dismissed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </PortalModal>
  );
}
