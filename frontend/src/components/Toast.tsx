// Inline glass toasts (no jarring browser alerts). A tiny local hook manages a
// list; <ToastStack> renders them, animating in/out with Framer Motion.

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useRef, useState } from "react";

export interface Toast {
  id: number;
  kind: "success" | "error";
  message: string;
}

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (kind: Toast["kind"], message: string) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, kind, message }]);
      // Auto-dismiss after a few seconds.
      window.setTimeout(() => dismiss(id), 4500);
    },
    [dismiss],
  );

  return { toasts, push, dismiss };
}

export function ToastStack({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => {
          const color = t.kind === "success" ? "var(--ok)" : "var(--danger)";
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 40, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, scale: 0.96 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="glass pointer-events-auto flex items-start gap-3 p-3.5"
              style={{ borderColor: `${color}59` }}
            >
              <span
                className="mt-0.5 inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: color, boxShadow: `0 0 12px ${color}` }}
              />
              <span className="text-fg text-sm leading-snug">{t.message}</span>
              <button
                type="button"
                className="ghost ml-auto -mr-1 -mt-1 shrink-0 px-2 py-1 text-xs"
                onClick={() => onDismiss(t.id)}
                aria-label="Dismiss"
              >
                ✕
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
