"use client";

import { useCallback, useSyncExternalStore } from "react";

// Trạng thái ngăn "Hỏi Viga" nằm ngoài cây React vì nút mở nằm ở thanh tiêu đề còn nút "Hỏi Viga về việc này"
// nằm trong trang chi tiết việc — cả hai đều mở cùng một ngăn.
type VigaState = { open: boolean; question: string | null; seq: number };

let state: VigaState = { open: false, question: null, seq: 0 };
const listeners = new Set<() => void>();

function set(next: VigaState): void {
  state = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

const SERVER: VigaState = { open: false, question: null, seq: 0 };

export function useVigaPanel() {
  const current = useSyncExternalStore(
    subscribe,
    () => state,
    () => SERVER,
  );

  const toggle = useCallback(() => set({ ...state, open: !state.open }), []);
  const close = useCallback(() => set({ ...state, open: false }), []);
  /** Mở ngăn và hỏi sẵn một câu (dùng ở nút "Hỏi Viga về việc này"). */
  const ask = useCallback((question: string) => set({ open: true, question, seq: state.seq + 1 }), []);

  return { ...current, toggle, close, ask };
}
