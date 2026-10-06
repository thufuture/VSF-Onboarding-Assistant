"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { vigaApi, VigaError } from "@/features/viga/api";
import type { TicketAttachmentResponseDTO } from "@/features/viga/dto/responseDTO/viga.response";

export const MAX_ATTACHMENTS = 5;
const IMAGE_MAX = 10 * 1024 * 1024;
const VIDEO_MAX = 50 * 1024 * 1024;
const IMAGE_EXT: Record<string, string[]> = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
  "image/gif": [".gif"],
};
const VIDEO_EXT: Record<string, string[]> = {
  "video/mp4": [".mp4"],
  "video/webm": [".webm"],
  "video/quicktime": [".mov"],
};
export const ACCEPT = [...Object.keys(IMAGE_EXT), ...Object.keys(VIDEO_EXT)].join(",");

export type AttachmentItem = {
  localId: number;
  name: string;
  kind: "IMAGE" | "VIDEO";
  /** Ảnh xem thử ngay trên máy (chưa phải URL đã lưu). */
  preview: string | null;
  status: "uploading" | "done" | "error";
  /** Khóa dịch của lỗi (`attachments.errors.*`). */
  errorKey: string | null;
  saved: TicketAttachmentResponseDTO | null;
};

/** Kiểm tra trước khi tải để báo lỗi ngay, không phải chờ máy chủ; trả loại tệp hoặc khóa lỗi. */
export function checkFile(file: Pick<File, "type" | "name" | "size">): { kind: "IMAGE" | "VIDEO" } | { errorKey: string } {
  const name = file.name.toLowerCase();
  const ext = name.includes(".") ? name.slice(name.lastIndexOf(".")) : "";
  if (IMAGE_EXT[file.type]?.includes(ext)) return file.size > IMAGE_MAX ? { errorKey: "tooLargeImage" } : { kind: "IMAGE" };
  if (VIDEO_EXT[file.type]?.includes(ext)) return file.size > VIDEO_MAX ? { errorKey: "tooLargeVideo" } : { kind: "VIDEO" };
  return { errorKey: "type" };
}

function errorKeyOf(caught: unknown): string {
  const apiCode = caught instanceof VigaError ? caught.apiCode : null;
  switch (apiCode) {
    case "ATTACHMENT_TYPE_NOT_ALLOWED":
      return "type";
    case "ATTACHMENT_TOO_LARGE":
      return "tooLargeImage";
    case "ATTACHMENTS_UNAVAILABLE":
      return "unavailable";
    default:
      return "failed";
  }
}

/** Ảnh và video đính kèm khi gửi ticket: tải lên ngay lúc chọn, giữ mã để gắn vào tin nhắn khi gửi, bỏ được từng tệp. */
export function useAttachments() {
  const [items, setItems] = useState<AttachmentItem[]>([]);
  const seq = useRef(0);
  const previews = useRef(new Set<string>());

  useEffect(() => {
    const urls = previews.current;
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const patch = useCallback((localId: number, next: Partial<AttachmentItem>) => {
    setItems((current) => current.map((item) => (item.localId === localId ? { ...item, ...next } : item)));
  }, []);

  const add = useCallback(
    (files: File[]) => {
      const room = MAX_ATTACHMENTS - items.filter((item) => item.status !== "error").length;
      files.forEach((file, index) => {
        seq.current += 1;
        const localId = seq.current;
        const failed = (errorKey: string): AttachmentItem => ({
          localId,
          name: file.name,
          kind: "IMAGE",
          preview: null,
          status: "error",
          errorKey,
          saved: null,
        });
        if (index >= room) {
          setItems((current) => [...current, failed("tooMany")]);
          return;
        }
        const checked = checkFile(file);
        if ("errorKey" in checked) {
          setItems((current) => [...current, failed(checked.errorKey)]);
          return;
        }
        const preview = checked.kind === "IMAGE" ? URL.createObjectURL(file) : null;
        if (preview) previews.current.add(preview);
        setItems((current) => [
          ...current,
          { localId, name: file.name, kind: checked.kind, preview, status: "uploading", errorKey: null, saved: null },
        ]);
        vigaApi
          .uploadTicketAttachment(file)
          .then((saved) => patch(localId, { status: "done", saved }))
          .catch((caught: unknown) => patch(localId, { status: "error", errorKey: errorKeyOf(caught) }));
      });
    },
    [items, patch],
  );

  const remove = useCallback(
    (localId: number) => {
      const item = items.find((row) => row.localId === localId);
      setItems((current) => current.filter((row) => row.localId !== localId));
      if (item?.saved) void vigaApi.discardTicketAttachment(item.saved.id).catch(() => undefined);
    },
    [items],
  );

  const reset = useCallback(() => setItems([]), []);

  return {
    items,
    add,
    remove,
    reset,
    /** Mã các tệp đã tải xong, để gắn vào tin nhắn. */
    ids: items.flatMap((item) => (item.saved ? [item.saved.id] : [])),
    uploading: items.some((item) => item.status === "uploading"),
    full: items.filter((item) => item.status !== "error").length >= MAX_ATTACHMENTS,
  };
}
