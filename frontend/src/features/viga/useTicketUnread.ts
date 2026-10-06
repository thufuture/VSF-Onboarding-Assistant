"use client";

import { useEffect, useState } from "react";

import { vigaApi } from "@/features/viga/api";

/** Phát khi người dùng vừa mở một ticket (đã đánh dấu đã xem): huy hiệu và danh sách tải lại ngay, không đợi lượt hỏi kế tiếp. */
export const TICKETS_READ_EVENT = "portal-tickets-read";

const POLL_MS = 30_000;

export function notifyTicketsRead(): void {
  window.dispatchEvent(new Event(TICKETS_READ_EVENT));
}

/**
 * Số ticket đang có tin chưa xem của người đăng nhập (mỗi ticket tính một). Hỏi lại mỗi 30 giây, khi quay lại tab và ngay sau khi
 * mở một ticket. Chưa phải realtime: tin mới hiện sau tối đa 30 giây (kế hoạch realtime làm sau).
 */
export function useTicketUnread(enabled = true): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    async function load() {
      try {
        const result = await vigaApi.getUnreadTickets();
        if (!cancelled) setCount(result.count);
      } catch {
        /* giữ số cũ */
      }
    }
    void load();
    const timer = window.setInterval(() => {
      if (!document.hidden) void load();
    }, POLL_MS);
    const onVisible = () => {
      if (!document.hidden) void load();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener(TICKETS_READ_EVENT, load);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener(TICKETS_READ_EVENT, load);
    };
  }, [enabled]);

  return enabled ? count : 0;
}
