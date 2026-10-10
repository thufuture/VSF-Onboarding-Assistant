"use client";

import { Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import styles from "./PdfViewer.module.scss";

type PdfDocument = import("pdfjs-dist").PDFDocumentProxy;

const MAX_PAGE_WIDTH = 980;
const A4_RATIO = 1.414;
const ZOOM_MIN = 40;
const ZOOM_MAX = 200;
const ZOOM_STEP = 10;
const ZOOM_FIT = 100;
const ZOOM_DEFAULT = 75;

const clampZoom = (value: number) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value));

/** Trình xem PDF của trang (vẽ từng trang lên canvas bằng pdf.js) thay cho khung PDF có sẵn của trình duyệt (thanh công cụ vẽ, ghi chú…).
 * Chỉ vẽ trang đang gần khung nhìn nên PDF dài vẫn nhẹ; nền xám, trang trắng như bộ đọc Markdown. */
export function PdfViewer({ url, label }: { url: string; label: string }) {
  const [doc, setDoc] = useState<PdfDocument | null>(null);
  const [failed, setFailed] = useState(false);
  const [base, setBase] = useState(0);
  const [zoom, setZoom] = useState(ZOOM_DEFAULT);
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
    const observer = new ResizeObserver(() => setBase(Math.max(280, Math.min(MAX_PAGE_WIDTH, element.clientWidth - 32))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Ctrl + cuộn chuột để phóng to / thu nhỏ (cuộn thường vẫn là cuộn trang).
  useEffect(() => {
    const element = scroller.current;
    if (!element) return;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      setZoom((current) => clampZoom(current + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP)));
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, []);

  const width = Math.round((base * zoom) / 100);

  return (
    <div aria-label={label} className={styles.root} role="group">
      <div className={styles.toolbar}>
        <button aria-label="Thu nhỏ" disabled={zoom <= ZOOM_MIN} onClick={() => setZoom(clampZoom(zoom - ZOOM_STEP))} type="button">
          <ZoomOut aria-hidden="true" size={15} />
        </button>
        <span aria-live="polite">{zoom}%</span>
        <button aria-label="Phóng to" disabled={zoom >= ZOOM_MAX} onClick={() => setZoom(clampZoom(zoom + ZOOM_STEP))} type="button">
          <ZoomIn aria-hidden="true" size={15} />
        </button>
        <button aria-label="Vừa chiều ngang" onClick={() => setZoom(ZOOM_FIT)} type="button">
          <Maximize2 aria-hidden="true" size={14} />
        </button>
        {doc ? <small>{doc.numPages} trang</small> : null}
      </div>
      <div className={styles.scroller} ref={scroller}>
        {failed ? <p className={styles.note}>Không mở được file.</p> : null}
        {!doc && !failed ? <p className={styles.note}>…</p> : null}
        {doc && width > 0
          ? Array.from({ length: doc.numPages }, (_, index) => (
              <PdfPage doc={doc} key={index} number={index + 1} total={doc.numPages} width={width} />
            ))
          : null}
      </div>
    </div>
  );
}

function PdfPage({ doc, number, total, width }: { doc: PdfDocument; number: number; total: number; width: number }) {
  const box = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [near, setNear] = useState(false);
  const [ratioHW, setRatioHW] = useState(A4_RATIO);
  const height = Math.round(width * ratioHW);

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
        // Vẽ dày hơn màn hình 1,5 lần để chữ và ảnh scan không bị mềm khi thu nhỏ vừa khung.
        const ratio = Math.min(3, Math.max(1, window.devicePixelRatio || 1) * 1.5);
        const target = canvas.current;
        target.width = Math.floor(viewport.width * ratio);
        target.height = Math.floor(viewport.height * ratio);
        setRatioHW(base.height / base.width);
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
