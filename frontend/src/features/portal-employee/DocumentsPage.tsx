"use client";

import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { FlatIcon } from "@/components/flat-icons/FlatIcon";
import { DocumentModal } from "@/features/chat/DocumentModal";
import { portalHrApi } from "@/features/portal-hr/api";
import { categoryStyle } from "@/features/portal-hr/docCategory";
import type { EmployeeDocumentResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { useSession } from "@/features/auth/SessionProvider";

import shared from "./employee.module.scss";
import styles from "./DocumentsPage.module.scss";
import { PageHero } from "./PageHero";

/** Thư viện tài liệu của nhân viên: lọc theo nhóm, tìm theo tên, bấm để đọc nội dung ngay trong trang. */
export function EmployeeDocumentsPage() {
  const t = useTranslations("employee.documents");
  const { user } = useSession();
  const [documents, setDocuments] = useState<EmployeeDocumentResponseDTO[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [open, setOpen] = useState<EmployeeDocumentResponseDTO | null>(null);

  useEffect(() => {
    let cancelled = false;
    portalHrApi
      .listMyDocuments()
      .then((result) => {
        if (!cancelled) setDocuments(result);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const categories = useMemo(() => {
    const seen = new Map<string, string>();
    for (const document of documents ?? []) seen.set(document.category_slug, document.category_name);
    return [...seen].map(([slug, name]) => ({ slug, name }));
  }, [documents]);

  const shown = (documents ?? []).filter(
    (document) =>
      (!category || document.category_slug === category) &&
      (!query.trim() || document.title.toLowerCase().includes(query.trim().toLowerCase())),
  );

  return (
    <>
      <PageHero
        avatarName={user.display_name}
        compact
        subtitle={t("subtitle")}
        title={t("title")}
      />

      <div className={shared.container}>
        {failed ? <p className={shared.banner}>{t("failed")}</p> : null}

        <div className={`${shared.card} ${shared.rise} ${styles.filters}`}>
          <label className={styles.search}>
            <Search aria-hidden="true" size={15} />
            <input
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("searchPlaceholder")}
              type="search"
              value={query}
            />
          </label>
          <div className={styles.chips}>
            <button className={`${styles.chip} ${category === "" ? styles.chipOn : ""}`} onClick={() => setCategory("")} type="button">
              {t("allCategories")}
            </button>
            {categories.map((item) => {
              const style = categoryStyle(item.name, 13);
              return (
                <button
                  className={`${styles.chip} ${category === item.slug ? styles.chipOn : ""}`}
                  key={item.slug}
                  onClick={() => setCategory(item.slug)}
                  type="button"
                >
                  {style.icon} {item.name}
                </button>
              );
            })}
          </div>
        </div>

        {documents === null && !failed ? (
          <div className={styles.grid}>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div className={shared.skeleton} key={i} style={{ height: 132 }} />
            ))}
          </div>
        ) : shown.length === 0 ? (
          <div className={`${shared.card} ${shared.empty}`}>
            <FlatIcon name="book" size={36} tone="indigo" />
            <b>{t("emptyTitle")}</b>
            <span>{t("emptyBody")}</span>
          </div>
        ) : (
          <div className={styles.grid}>
            {shown.map((document, i) => {
              const style = categoryStyle(document.category_name, 15);
              return (
                <button
                  className={`${shared.card} ${shared.hoverable} ${shared.rise} ${styles.doc} ${styles[style.tone]}`}
                  key={document.id}
                  onClick={() => setOpen(document)}
                  style={{ "--i": i % 8 } as never}
                  type="button"
                >
                  <span className={styles.docIcon}>{style.icon}</span>
                  <b>{document.title}</b>
                  <span className={styles.docMeta}>
                    <span className={styles.docCat}>{document.category_name}</span>
                    <span>{t("sections", { count: document.section_count })}</span>
                  </span>
                  <span className={styles.docOpen}>{t("read")}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {open ? (
        <DocumentModal
          documentTitle={open.title}
          documentUrl=""
          onClose={() => setOpen(null)}
          sectionHeading={null}
          versionId={open.latest_version_id}
          versionLabel={open.category_name}
        />
      ) : null}
    </>
  );
}
