// Presentation metadata for the five memory types. Colors match the --mt-*
// tokens in index.css. Icons are lucide-react components (no emoji). Kept in one
// place so every badge/label/legend agrees.

import {
  Circle,
  Code2,
  FileText,
  MessagesSquare,
  Scale,
  Workflow,
  type LucideIcon,
} from "lucide-react";

export interface MemoryTypeMeta {
  label: string;
  color: string; // hex, so we can compose alpha tints (color + "1f", etc.)
  Icon: LucideIcon;
}

export const MEMORY_TYPE_META: Record<string, MemoryTypeMeta> = {
  document: { label: "Document", color: "#38bdf8", Icon: FileText },
  code: { label: "Code", color: "#34d399", Icon: Code2 },
  decision: { label: "Decision", color: "#fbbf24", Icon: Scale },
  workflow: { label: "Workflow", color: "#a78bfa", Icon: Workflow },
  conversation: { label: "Conversation", color: "#f472b6", Icon: MessagesSquare },
};

const FALLBACK: MemoryTypeMeta = { label: "Memory", color: "#9aa1b1", Icon: Circle };

export function memoryMeta(type: string | null | undefined): MemoryTypeMeta {
  if (!type) return FALLBACK;
  return MEMORY_TYPE_META[type] ?? { ...FALLBACK, label: type };
}
