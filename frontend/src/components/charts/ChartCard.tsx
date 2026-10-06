"use client";

import { Table2, BarChart3 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import styles from "./Charts.module.scss";

export type ChartTable = { head: string[]; rows: (string | number)[][] };

/**
 * Khung một biểu đồ: tiêu đề, mô tả ngắn, nút chuyển sang bảng số liệu (cùng dữ liệu, cho người dùng đọc màn hình hoặc cần
 * đối chiếu số) và vùng biểu đồ. Chứa các biến màu biểu đồ nên mọi biểu đồ phải nằm trong khung này.
 */
export function ChartCard({
  title,
  subtitle,
  table,
  wide = false,
  children,
}: {
  title: string;
  subtitle?: string;
  table: ChartTable;
  wide?: boolean;
  children: ReactNode;
}) {
  const t = useTranslations("analytics");
  const [asTable, setAsTable] = useState(false);

  return (
    <section className={`${styles.card} ${wide ? styles.wide : ""}`}>
      <header className={styles.cardHead}>
        <div>
          <h3>{title}</h3>
          {subtitle ? <small>{subtitle}</small> : null}
        </div>
        <button
          aria-pressed={asTable}
          className={styles.toggle}
          onClick={() => setAsTable((value) => !value)}
          title={asTable ? t("viewChart") : t("viewTable")}
          type="button"
        >
          {asTable ? <BarChart3 aria-hidden="true" size={13} /> : <Table2 aria-hidden="true" size={13} />}
          {asTable ? t("viewChart") : t("viewTable")}
        </button>
      </header>
      {asTable ? (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                {table.head.map((cell) => (
                  <th key={cell}>{cell}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.length === 0 ? (
                <tr>
                  <td colSpan={table.head.length}>{t("empty")}</td>
                </tr>
              ) : (
                table.rows.map((row, index) => (
                  <tr key={index}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>{cell}</td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        children
      )}
    </section>
  );
}
