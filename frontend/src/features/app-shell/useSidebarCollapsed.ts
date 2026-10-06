"use client";

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "vsf-sidebar-collapsed";

const listeners = new Set<() => void>();
// Trình duyệt chặn lưu trữ: giữ trạng thái trong bộ nhớ để nút vẫn chạy, chỉ không nhớ lần sau.
let memory: boolean | null = null;

function read(): boolean {
  if (memory !== null) return memory;
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

/** Thu gọn/mở rộng thanh bên trên máy tính để trang làm việc rộng hơn; nhớ lựa chọn ở lần vào sau. */
export function useSidebarCollapsed(): { collapsed: boolean; toggleCollapsed: () => void } {
  const collapsed = useSyncExternalStore(subscribe, read, () => false);

  const toggleCollapsed = useCallback(() => {
    const next = !read();
    memory = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    } catch {
      // Không lưu được: vẫn đổi trạng thái trong phiên này.
    }
    listeners.forEach((listener) => listener());
  }, []);

  return { collapsed, toggleCollapsed };
}
