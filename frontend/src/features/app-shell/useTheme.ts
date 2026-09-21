"use client";

import { useCallback, useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "vsf-theme";

const listeners = new Set<() => void>();
// Trình duyệt chặn lưu trữ (chế độ riêng tư): giữ lựa chọn trong bộ nhớ để nút vẫn chạy, chỉ không nhớ lần sau.
let memory: Theme | null = null;

function read(): Theme {
  if (memory) return memory;
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // Không đọc được lựa chọn đã lưu: dùng giao diện sáng.
  }
  return "light";
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

/**
 * Giao diện sáng/tối của khu đã đăng nhập. Server luôn vẽ "light"; client đọc lựa chọn đã lưu ngay sau khi hydrate
 * (useSyncExternalStore giữ HTML server và client khớp nhau), và đồng bộ giữa các tab.
 */
export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const theme = useSyncExternalStore(subscribe, read, () => "light" as Theme);

  const toggleTheme = useCallback(() => {
    const next: Theme = read() === "dark" ? "light" : "dark";
    memory = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Không lưu được: chỉ áp dụng cho lần xem này.
    }
    listeners.forEach((listener) => listener());
  }, []);

  return { theme, toggleTheme };
}
