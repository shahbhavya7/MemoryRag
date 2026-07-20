// Evaluation dashboard (Phase 9d): run the routing-accuracy eval on demand
// (POST /evaluation/run) and render it in glass — an animated count-up for
// overall accuracy, per-type bars that grow to their value, and a table of
// expected-vs-predicted with mismatches highlighted.

import { motion, useReducedMotion } from "framer-motion";
import { Check, X } from "lucide-react";
import { useState } from "react";

import { api, ApiError } from "../api/client";
import type { EvalResponse } from "../api/types";
import { GlassCard } from "../components/GlassPanel";
import MemoryBadge from "../components/MemoryBadge";
import CountUp from "../components/reactbits/CountUp";
import { memoryMeta } from "../lib/memoryTypes";

function AccuracyStat({ data }: { data: EvalResponse }) {
  const pct = Math.round(data.accuracy * 100);
  return (
    <GlassCard strong className="flex items-center gap-6">
      <div>
        <div className="text-eyebrow">Routing accuracy</div>
        <div className="mt-1 flex items-baseline text-5xl font-extrabold tracking-tight">
          {/* React Bits CountUp animates the headline number from 0 → value. */}
          <CountUp to={pct} duration={1.1} className="brand-gradient" />
          <span className="brand-gradient">%</span>
        </div>
        <div className="text-fg-muted mt-1 text-sm">
          {data.correct} / {data.total} correct · prompt{" "}
          <span className="text-fg font-mono">{data.version}</span>
        </div>
      </div>
    </GlassCard>
  );
}

function PerTypeBars({ data }: { data: EvalResponse }) {
  const reduce = useReducedMotion();
  return (
    <GlassCard>
      <h2>Per memory type</h2>
      <div className="mt-4 flex flex-col gap-3.5">
        {data.per_type.map((row, i) => {
          const meta = memoryMeta(row.memory_type);
          const pct = row.accuracy * 100;
          return (
            <div key={row.memory_type}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="inline-flex items-center gap-2 font-medium" style={{ color: meta.color }}>
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: meta.color }} />
                  {meta.label}
                </span>
                <span className="text-fg-muted">
                  {row.correct}/{row.total}
                </span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/8">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: meta.color }}
                  initial={reduce ? false : { width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.7, delay: 0.1 + i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

function ResultsTable({ data }: { data: EvalResponse }) {
  return (
    <GlassCard className="overflow-hidden">
      <h2>Questions</h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-fg-muted text-left text-xs">
              <th className="px-2 py-2 font-semibold">Question</th>
              <th className="px-2 py-2 font-semibold">Expected</th>
              <th className="px-2 py-2 font-semibold">Predicted</th>
              <th className="px-2 py-2 font-semibold">Result</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r, i) => (
              <motion.tr
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                style={{ background: r.correct ? undefined : "rgba(251,113,133,0.10)" }}
                className="border-t border-white/8"
              >
                <td className="text-fg px-2 py-2.5">{r.question}</td>
                <td className="px-2 py-2.5">
                  <MemoryBadge type={r.expected} size="sm" />
                </td>
                <td className="px-2 py-2.5">
                  <span className="flex flex-wrap gap-1">
                    {r.predicted.length ? (
                      r.predicted.map((p, j) => <MemoryBadge key={p} type={p} size="sm" index={j} />)
                    ) : (
                      <span className="text-fg-faint">—</span>
                    )}
                  </span>
                </td>
                <td className="px-2 py-2.5">
                  {r.correct ? (
                    <Check size={16} style={{ color: "var(--ok)" }} />
                  ) : (
                    <span
                      className="inline-flex items-center gap-1 font-semibold"
                      style={{ color: "var(--danger)" }}
                    >
                      <X size={14} /> miss
                    </span>
                  )}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}

export default function EvaluationPage() {
  const [data, setData] = useState<EvalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setData(await api.runEvaluation());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Evaluation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <h1>Evaluation</h1>
          <p className="text-fg-muted mt-1">
            Runs the hand-labeled routing gold set through the classifier and scores accuracy.
          </p>
        </div>
        <button type="button" className="primary" onClick={() => void run()} disabled={loading}>
          {loading ? "Running…" : data ? "Re-run" : "Run evaluation"}
        </button>
      </div>

      {error && (
        <GlassCard strong className="max-w-lg">
          <p style={{ color: "var(--danger)" }}>{error}</p>
        </GlassCard>
      )}

      {loading && (
        <div className="flex flex-col gap-5">
          <div className="shimmer glass h-28" />
          <div className="shimmer glass h-56" />
          <div className="shimmer glass h-72" />
        </div>
      )}

      {!loading && !data && !error && (
        <GlassCard className="max-w-lg">
          <p className="text-fg-muted">
            Click <strong className="text-fg">Run evaluation</strong> to score the router. It makes one
            classifier call per question, so it takes a few seconds.
          </p>
        </GlassCard>
      )}

      {!loading && data && (
        <div className="flex flex-col gap-5">
          <AccuracyStat data={data} />
          <PerTypeBars data={data} />
          <ResultsTable data={data} />
        </div>
      )}
    </div>
  );
}
