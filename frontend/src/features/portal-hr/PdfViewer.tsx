"use client";

import { useEffect, useRef, useState } from "react";

import styles from "./PdfViewer.module.scss";

type PdfDocument = import("pdfjs-dist").PDFDocumentProxy;

const MAX_PAGE_WIDTH = 980;
const A4_RATIO = 1.414;

/** Trình xem PDF của trang (vẽ từng trang lên canvas bằng pdf.js) thay cho khung PDF có sẵn của trình duyệt (thanh công cụ vẽ, ghi chú…).
 * Chỉ vẽ trang đang gần khung nhìn nên PDF dài vẫn nhẹ; nền xám, trang trắng như bộ đọc Markdown. */
export function PdfViewer({ url, label }: { url: string; label: string }) {
  const [doc, setDoc] = useState<PdfDocument | null>(null);
  const [failed, setFailed] = useState(false);
  const [width, setWidth] = useState(0);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    let task: { destroy: () => Promise<void> } | null = null;
    void (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        if (cancelled) return;
        pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
        const loading = pdfjs.getDocument({ url, withCredentials: true });
        task = loading;
        const opened = await loading.promise;
        if (!cancelled) setDoc(opened);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      void task?.destroy();
    };
  }, [url]);

  useEffect(() => {
    const element = scroller.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setWidth(Math.max(280, Math.min(MAX_PAGE_WIDTH, element.clientWidth - 32))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div aria-label={label} className={styles.scroller} ref={scroller}>
      {failed ? <p className={styles.note}>Không mở được file.</p> : null}
      {!doc && !failed ? <p className={styles.note}>…</p> : null}
      {doc && width > 0
        ? Array.from({ length: doc.numPages }, (_, index) => (
            <PdfPage doc={doc} key={index} number={index + 1} total={doc.numPages} width={width} />
          ))
        : null}
    </div>
  );
}

function PdfPage({ doc, number, total, width }: { doc: PdfDocument; number: number; total: number; width: number }) {
  const box = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [near, setNear] = useState(false);
  const [height, setHeight] = useState(Math.round(width * A4_RATIO));

  useEffect(() => {
    const element = box.current;
    if (!element) return;
    const observer = new IntersectionObserver((entries) => setNear(entries.some((entry) => entry.isIntersecting)), {
      rootMargin: "800px 0px",
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!near || !canvas.current) return;
    let task: { cancel: () => void } | null = null;
    let cancelled = false;
    void (async () => {
      try {
        const page = await doc.getPage(number);
        if (cancelled || !canvas.current) return;
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: width / base.width });
        const ratio = window.devicePixelRatio || 1;
        const target = canvas.current;
        target.width = Math.floor(viewport.width * ratio);
        target.height = Math.floor(viewport.height * ratio);
        setHeight(Math.round(viewport.height));
        const context = target.getContext("2d");
        if (!context) return;
        const render = page.render({
          canvas: target,
          canvasContext: context,
          viewport,
          transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0],
        });
        task = render;
        await render.promise;
      } catch {
        /* trang bị hủy khi cuộn đi hoặc đổi cỡ: bỏ qua */
      }
    })();
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [near, doc, number, width]);

  return (
    <div className={styles.page} ref={box} style={{ width, height }}>
      <canvas ref={canvas} style={{ width, height }} />
      <span className={styles.badge}>
        {number} / {total}
      </span>
    </div>
  );
}
