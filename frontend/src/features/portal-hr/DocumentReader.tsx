"use client";

import { useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./DocumentReader.module.scss";

type Section = { id: string; level: number; heading: string | null; body: string };

// Cùng quy tắc tách section với backend (H1–H3 mở section mới) để mục lục khớp nội dung đã ingest.
export function splitSections(markdown: string): Section[] {
  const sections: Section[] = [];
  let current: Section | null = null;
  for (const line of markdown.split("\n")) {
    const heading = /^(#{1,3})\s+(.+?)\s*$/.exec(line);
    if (heading) {
      current = { id: `sec-${sections.length}`, level: heading[1].length, heading: heading[2], body: "" };
      sections.push(current);
    } else {
      if (!current) {
        current = { id: `sec-${sections.length}`, level: 0, heading: null, body: "" };
        sections.push(current);
      }
      current.body += `${line}\n`;
    }
  }
  return sections.filter((s) => s.heading || s.body.trim());
}

/** Trình đọc tài liệu kiểu Word: mục lục đứng yên bên trái, trang giấy bên phải, làm nổi mục đang đọc theo vị trí cuộn. */
export function DocumentReader({ markdown, tocLabel }: { markdown: string; tocLabel: string }) {
  const sections = useMemo(() => splitSections(markdown), [markdown]);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [activeSec, setActiveSec] = useState<string | null>(null);

  function scrollToSection(id: string) {
    const box = canvasRef.current;
    const el = box?.querySelector<HTMLElement>(`#${id}`);
    if (!box || !el) return;
    const top = el.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop - 18;
    box.scrollTo({ top, behavior: "smooth" });
    setActiveSec(id);
  }

  function syncActiveSection() {
    const box = canvasRef.current;
    if (!box) return;
    const boxTop = box.getBoundingClientRect().top;
    let current: string | null = null;
    for (const item of sections) {
      if (!item.heading) continue;
      const el = box.querySelector<HTMLElement>(`#${item.id}`);
      if (el && el.getBoundingClientRect().top - boxTop <= 60) current = item.id;
    }
    setActiveSec(current);
  }

  return (
    <div className={styles.docRead}>
      <nav aria-label={tocLabel} className={styles.docToc}>
        <b>{tocLabel}</b>
        <div className={styles.docTocList}>
          {sections
            .filter((s) => s.heading)
            .map((s) => (
              <button
                className={`${styles[`lvl${s.level}`]} ${activeSec === s.id ? styles.tocOn : ""}`}
                key={s.id}
                onClick={() => scrollToSection(s.id)}
                type="button"
              >
                {s.heading}
              </button>
            ))}
        </div>
      </nav>
      <div className={styles.docCanvas} onScroll={syncActiveSection} ref={canvasRef}>
        <article className={styles.docPage}>
          {sections.map((s) => {
            const Heading = (s.level <= 1 ? "h2" : s.level === 2 ? "h3" : "h4") as "h2" | "h3" | "h4";
            return (
              <section id={s.id} key={s.id}>
                {s.heading ? <Heading className={styles[`hd${Math.max(s.level, 1)}`]}>{s.heading}</Heading> : null}
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{s.body}</ReactMarkdown>
              </section>
            );
          })}
        </article>
      </div>
    </div>
  );
}
