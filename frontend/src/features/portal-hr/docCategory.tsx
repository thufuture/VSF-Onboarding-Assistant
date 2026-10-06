import { BookOpen, FileText, Laptop, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import type { FlatIconName, FlatTone } from "@/components/flat-icons/FlatIcon";

export type DocTone = "blue" | "indigo" | "teal" | "rose" | "amber" | "slate";

/**
 * Màu + icon theo nhóm tài liệu (v15: DOC_TONE và icon theo nhóm) — nhận diện theo tên nhóm,
 * nhóm lạ dùng tông xanh. Dùng chung cho bảng Tài liệu và bộ chọn nguồn của "Tạo task bằng AI".
 */
export function categoryStyle(name: string, size = 12): { tone: DocTone; icon: ReactNode } {
  const n = name.toLowerCase();
  if (/onboarding/.test(n)) return { tone: "teal", icon: <FileText aria-hidden="true" size={size} /> };
  if (/đào tạo|training/.test(n)) return { tone: "indigo", icon: <BookOpen aria-hidden="true" size={size} /> };
  if (/thiết bị|device/.test(n)) return { tone: "teal", icon: <Laptop aria-hidden="true" size={size} /> };
  if (/bảo mật|security/.test(n)) return { tone: "rose", icon: <ShieldCheck aria-hidden="true" size={size} /> };
  if (/văn phòng|office/.test(n)) return { tone: "amber", icon: <FileText aria-hidden="true" size={size} /> };
  if (/quy trình|process/.test(n)) return { tone: "slate", icon: <FileText aria-hidden="true" size={size} /> };
  return { tone: "blue", icon: <FileText aria-hidden="true" size={size} /> };
}

/** Biểu tượng FlatIcon nhiều màu theo nhóm tài liệu (nhận diện theo tên; nhóm lạ dùng tài liệu xanh dương). */
export function categoryFlat(name: string): { icon: FlatIconName; tone: FlatTone } {
  const n = name.toLowerCase();
  if (/onboarding/.test(n)) return { icon: "route", tone: "teal" };
  if (/khác|other/.test(n)) return { icon: "file", tone: "slate" };
  if (/đào tạo|training/.test(n)) return { icon: "book", tone: "indigo" };
  if (/thiết bị|device/.test(n)) return { icon: "laptop", tone: "blue" };
  if (/bảo mật|security/.test(n)) return { icon: "alert", tone: "rose" };
  if (/văn phòng|office/.test(n)) return { icon: "building", tone: "amber" };
  return { icon: "file", tone: "blue" };
}
