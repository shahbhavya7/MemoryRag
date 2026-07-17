// Memories browser (Phase 9c): a responsive grid of memory cards, filterable by
// type. Filtering re-lays-out the grid with Framer Motion layout animations.
// Cards use the `lite` glass (no backdrop-filter) since a grid of blurred cards
// would be expensive — the blur guardrail.

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

import { api, ApiError } from "../api/client";
import { MEMORY_TYPES, type Memory } from "../api/types";
import { GlassCard, GlassPanel } from "../components/GlassPanel";
import { memoryMeta } from "../lib/memoryTypes";

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MemoriesPage() {
  const [all, setAll] = useState<Memory[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setAll(await api.listMemories());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load memories.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const m of all) c[m.memory_type] = (c[m.memory_type] ?? 0) + 1;
    return c;
  }, [all]);

  const filtered = filter === "all" ? all : all.filter((m) => m.memory_type === filter);

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1>Memories</h1>
          <p className="text-fg-muted mt-1">Everything stored across the five memory types.</p>
        </div>
        <button type="button" className="ghost" onClick={() => void load()} disabled={loading}>
          ↻ Refresh
        </button>
      </div>

      {/* Filter chips */}
      <div className="mb-5 flex flex-wrap gap-2">
        <FilterChip label="All" active={filter === "all"} count={all.length} onClick={() => setFilter("all")} />
        {MEMORY_TYPES.map((t) => (
          <FilterChip
            key={t}
            label={`${memoryMeta(t).emoji} ${memoryMeta(t).label}`}
            color={memoryMeta(t).color}
            active={filter === t}
            count={counts[t] ?? 0}
            onClick={() => setFilter(t)}
          />
        ))}
      </div>

      {error && (
        <GlassCard strong className="max-w-lg">
          <p style={{ color: "var(--danger)" }}>{error}</p>
        </GlassCard>
      )}

      {!error && loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="shimmer glass-lite h-36" />
          ))}
        </div>
      )}

      {!error && !loading && filtered.length === 0 && (
        <GlassCard className="max-w-lg">
          <p className="text-fg-muted">
            No memories {filter !== "all" ? `of type “${memoryMeta(filter).label}”` : "yet"}. Add some on
            the Upload page.
          </p>
        </GlassCard>
      )}

      {!error && !loading && filtered.length > 0 && (
        <motion.div layout className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {filtered.map((m) => {
              const meta = memoryMeta(m.memory_type);
              return (
                <motion.div
                  key={m.id}
                  layout
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.92 }}
                  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                >
                  <GlassPanel lite animateIn={false} interactive className="flex h-full flex-col p-4">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[0.68rem] font-semibold"
                        style={{ color: meta.color, borderColor: `${meta.color}59`, background: `${meta.color}1f` }}
                      >
                        <span aria-hidden="true">{meta.emoji}</span>
                        {meta.label}
                      </span>
                      <span className="text-fg-faint text-[0.68rem]">{formatDate(m.created_at)}</span>
                    </div>
                    <p className="text-fg line-clamp-5 text-sm leading-relaxed">{m.content}</p>
                    {m.source_ref && (
                      <div className="text-fg-muted mt-3 truncate font-mono text-[0.7rem]" title={m.source_ref}>
                        ⎘ {m.source_ref}
                      </div>
                    )}
                  </GlassPanel>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
}

function FilterChip({
  label,
  count,
  active,
  color,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  color?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full px-3 py-1.5 text-sm transition-colors"
      style={
        active
          ? {
              color: color ?? "var(--fg)",
              borderColor: `${color ?? "#7fb6ff"}80`,
              background: `${color ?? "#3b82f6"}26`,
            }
          : undefined
      }
    >
      {label} <span className="opacity-60">{count}</span>
    </button>
  );
}
