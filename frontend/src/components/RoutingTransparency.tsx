// The routing-transparency view for one answer. Lives INSIDE an assistant
// GlassCard, so it uses plain translucent sub-rows (no nested backdrop-filter).
// Shows: the token budget breakdown (kept vs dropped) from the Phase 7 context
// trace, and the retrieved source chunks with their scores.

import type { ChatSource, ContextTrace } from "../api/types";
import { memoryMeta } from "../lib/memoryTypes";

function TokenBar({ trace }: { trace: ContextTrace }) {
  const { system, history, context, total } = trace.tokens;
  const budget = trace.token_budget || total || 1;
  const pct = (n: number) => `${Math.min(100, (n / budget) * 100)}%`;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="text-fg-muted">
          Context budget · <span className="text-fg font-medium">{total}</span> / {budget} tokens
        </span>
        <span className="flex gap-2">
          <span style={{ color: "var(--ok)" }}>{trace.kept_count} kept</span>
          <span style={{ color: trace.dropped_count ? "var(--danger)" : "var(--fg-faint)" }}>
            {trace.dropped_count} dropped
          </span>
        </span>
      </div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-white/8">
        <div style={{ width: pct(system), background: "var(--fg-faint)" }} title={`system ${system}`} />
        <div style={{ width: pct(history), background: "var(--accent-2)" }} title={`history ${history}`} />
        <div style={{ width: pct(context), background: "var(--accent)" }} title={`context ${context}`} />
      </div>
      <div className="text-fg-muted mt-1.5 flex gap-3 text-[0.68rem]">
        <Legend color="var(--fg-faint)" label={`system ${system}`} />
        <Legend color="var(--accent-2)" label={`history ${history}`} />
        <Legend color="var(--accent)" label={`context ${context}`} />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function RetrievedRow({
  memoryType,
  score,
  tokens,
  kept,
  text,
}: {
  memoryType: string | null;
  score: number;
  tokens?: number;
  kept?: boolean;
  text: string;
}) {
  const meta = memoryMeta(memoryType);
  return (
    <div
      className="rounded-xl border border-white/8 bg-white/5 p-2.5"
      style={{ opacity: kept === false ? 0.55 : 1 }}
    >
      <div className="mb-1 flex items-center gap-2 text-[0.7rem]">
        <span className="inline-flex items-center gap-1.5 font-semibold" style={{ color: meta.color }}>
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: meta.color }} />
          {meta.label}
        </span>
        {kept !== undefined && (
          <span
            className="rounded px-1.5 py-0.5 font-medium"
            style={{
              color: kept ? "var(--ok)" : "var(--danger)",
              background: kept ? "rgba(52,211,153,0.14)" : "rgba(251,113,133,0.14)",
            }}
          >
            {kept ? "kept" : "dropped"}
          </span>
        )}
        <span className="text-fg-faint ml-auto font-mono">
          {score.toFixed(3)}
          {tokens !== undefined ? ` · ${tokens} tok` : ""}
        </span>
      </div>
      <div className="mb-1.5 h-1 w-full overflow-hidden rounded-full bg-white/8">
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.max(4, Math.min(100, score * 100))}%`, background: meta.color }}
        />
      </div>
      <p className="text-fg-muted line-clamp-2 text-xs leading-snug">{text}</p>
    </div>
  );
}

export default function RoutingTransparency({
  sources,
  trace,
  traceLoading,
}: {
  sources: ChatSource[];
  trace: ContextTrace | null;
  traceLoading: boolean;
}) {
  return (
    <div className="mt-3 border-t border-white/10 pt-3">
      <div className="text-eyebrow mb-2.5">Routing & context</div>

      {trace ? (
        <div className="flex flex-col gap-3">
          <TokenBar trace={trace} />
          <div className="flex flex-col gap-2">
            {trace.retrieved.map((r, i) => (
              <RetrievedRow
                key={i}
                memoryType={r.memory_type}
                score={r.score}
                tokens={r.tokens}
                kept={r.kept}
                text={r.preview}
              />
            ))}
          </div>
        </div>
      ) : traceLoading ? (
        <div className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="shimmer h-14 rounded-xl border border-white/8 bg-white/5" />
          ))}
        </div>
      ) : sources.length ? (
        // Fallback: no trace available -> show the kept sources from /chat.
        <div className="flex flex-col gap-2">
          {sources.map((s, i) => (
            <RetrievedRow key={i} memoryType={s.memory_type} score={s.score} text={s.text} />
          ))}
        </div>
      ) : (
        <p className="text-fg-faint text-xs">No sources retrieved for this answer.</p>
      )}
    </div>
  );
}
