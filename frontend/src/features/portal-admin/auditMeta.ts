import {
  Building2,
  Copy,
  GitBranch,
  History,
  KeyRound,
  Lock,
  Unlock,
  UserPlus,
  Users,
  FileText,
  type LucideIcon,
} from "lucide-react";

import type { Tone } from "./adminUi";

// Biểu tượng + tông màu cho từng loại hành động trong nhật ký (v15: `admLog(act, target, icon, tone)`).
const META: Record<string, { icon: LucideIcon; tone: Tone }> = {
  CREATE_USER: { icon: UserPlus, tone: "Teal" },
  UPDATE_USER: { icon: Users, tone: "Blue" },
  RESET_PASSWORD: { icon: KeyRound, tone: "Amber" },
  LOCK_USER: { icon: Lock, tone: "Rose" },
  UNLOCK_USER: { icon: Unlock, tone: "Teal" },
  CREATE_TEAM: { icon: Building2, tone: "Blue" },
  UPDATE_TEAM: { icon: Building2, tone: "Blue" },
  ARCHIVE_TEAM: { icon: Building2, tone: "Slate" },
  RESTORE_TEAM: { icon: Building2, tone: "Teal" },
  ADD_MEMBER: { icon: Users, tone: "Teal" },
  REMOVE_MEMBER: { icon: Users, tone: "Rose" },
  COPY_TEMPLATE: { icon: Copy, tone: "Indigo" },
  PUBLISH_TEMPLATE: { icon: GitBranch, tone: "Indigo" },
  INGEST_DOCUMENT: { icon: FileText, tone: "Blue" },
};

export function auditIcon(action: string): LucideIcon {
  return META[action]?.icon ?? History;
}

export function auditTone(action: string): Tone {
  return META[action]?.tone ?? "Slate";
}
