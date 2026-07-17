// Presentation metadata for the five memory types. Colors match the --mt-*
// tokens in index.css. Kept in one place so every badge/label/legend agrees.

export interface MemoryTypeMeta {
  label: string;
  color: string; // hex, so we can compose alpha tints (color + "1f", etc.)
  emoji: string;
}

export const MEMORY_TYPE_META: Record<string, MemoryTypeMeta> = {
  document: { label: "Document", color: "#38bdf8", emoji: "📄" },
  code: { label: "Code", color: "#34d399", emoji: "💻" },
  decision: { label: "Decision", color: "#fbbf24", emoji: "⚖️" },
  workflow: { label: "Workflow", color: "#a78bfa", emoji: "🔀" },
  conversation: { label: "Conversation", color: "#f472b6", emoji: "💬" },
};

const FALLBACK: MemoryTypeMeta = { label: "Memory", color: "#9aa1b1", emoji: "•" };

export function memoryMeta(type: string | null | undefined): MemoryTypeMeta {
  if (!type) return FALLBACK;
  return MEMORY_TYPE_META[type] ?? { ...FALLBACK, label: type };
}
