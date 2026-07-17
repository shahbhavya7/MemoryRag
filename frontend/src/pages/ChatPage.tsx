// The Chat page: a message thread + input calling POST /chat (the Phase 6
// routing graph), scoped to the selected project. Each answer shows the router's
// decision as prominent memory-type badges, plus a routing-transparency panel
// (sources + Phase 7 token breakdown from GET /context-trace/{message_id}).

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { api, ApiError } from "../api/client";
import type { ChatSource, ContextTrace } from "../api/types";
import { GlassCard, GlassPanel } from "../components/GlassPanel";
import MemoryBadge from "../components/MemoryBadge";
import RoutingTransparency from "../components/RoutingTransparency";
import { useProjects } from "../project/ProjectContext";

interface UserMsg {
  id: number;
  role: "user";
  content: string;
}
interface AssistantMsg {
  id: number;
  role: "assistant";
  content: string;
  memoryTypes: string[];
  sources: ChatSource[];
  trace: ContextTrace | null;
  traceLoading: boolean;
  error?: boolean;
}
type Msg = UserMsg | AssistantMsg;

const SUGGESTIONS = [
  "Why did we choose PostgreSQL over MongoDB?",
  "How do we deploy the backend?",
  "What does the slugify function do?",
  "What is the office WiFi network name?",
  "What did the team decide about Friday deploys?",
];

export default function ChatPage() {
  const { selectedProjectId, selectedProject } = useProjects();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const reduce = useReducedMotion();
  const nextId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  }, [messages, pending, reduce]);

  // Reset the thread when switching projects (chat is project-scoped).
  useEffect(() => {
    setMessages([]);
  }, [selectedProjectId]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || pending || !selectedProjectId) return;

    setInput("");
    setMessages((prev) => [...prev, { id: nextId.current++, role: "user", content: question }]);
    setPending(true);

    try {
      const res = await api.sendChat(selectedProjectId, question);
      const assistantId = nextId.current++;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: res.answer,
          memoryTypes: res.memory_types ?? [],
          sources: res.sources ?? [],
          trace: null,
          traceLoading: res.message_id != null,
        },
      ]);

      // Fetch the context trace for the token breakdown (kept vs dropped).
      if (res.message_id != null) {
        api
          .getContextTrace(res.message_id)
          .then((trace) =>
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId && m.role === "assistant"
                  ? { ...m, trace, traceLoading: false }
                  : m,
              ),
            ),
          )
          .catch(() =>
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId && m.role === "assistant"
                  ? { ...m, traceLoading: false }
                  : m,
              ),
            ),
          );
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Something went wrong.";
      setMessages((prev) => [
        ...prev,
        {
          id: nextId.current++,
          role: "assistant",
          content: msg,
          memoryTypes: [],
          sources: [],
          trace: null,
          traceLoading: false,
          error: true,
        },
      ]);
    } finally {
      setPending(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  if (!selectedProjectId) {
    return (
      <GlassCard className="max-w-lg">
        <h1>Chat</h1>
        <p className="text-fg-muted mt-2">
          Select or create a project in the top bar to start chatting.
        </p>
      </GlassCard>
    );
  }

  const rise = reduce
    ? {}
    : { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] as const } };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      {/* Thread */}
      <div className="flex-1 space-y-4 overflow-auto pb-4 pr-1">
        {messages.length === 0 && (
          <GlassCard className="mt-2">
            <h2>Ask MemoryRAG</h2>
            <p className="text-fg-muted mt-1">
              Questions are routed to the right memory type in{" "}
              <strong className="text-fg">{selectedProject?.name}</strong>. Try one:
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {SUGGESTIONS.map((q) => (
                <button key={q} type="button" onClick={() => void send(q)} className="text-sm">
                  {q}
                </button>
              ))}
            </div>
          </GlassCard>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <motion.div key={m.id} {...rise} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-md border border-white/10 bg-[rgba(34,150,230,0.18)] px-4 py-2.5 text-fg">
                {m.content}
              </div>
            </motion.div>
          ) : (
            <GlassPanel key={m.id} className="p-4">
              {m.memoryTypes.length > 0 && (
                <div className="mb-2.5 flex flex-wrap items-center gap-2">
                  <span className="text-fg-faint text-[0.68rem]">routed to</span>
                  {m.memoryTypes.map((t, i) => (
                    <MemoryBadge key={t} type={t} index={i} />
                  ))}
                </div>
              )}
              <p
                className="whitespace-pre-wrap leading-relaxed"
                style={{ color: m.error ? "var(--danger)" : "var(--fg)" }}
              >
                {m.content}
              </p>
              {!m.error && (
                <RoutingTransparency sources={m.sources} trace={m.trace} traceLoading={m.traceLoading} />
              )}
            </GlassPanel>
          ),
        )}

        <AnimatePresence>
          {pending && (
            <motion.div
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={reduce ? undefined : { opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 px-2 text-fg-muted"
            >
              <span className="flex gap-1">
                <Dot i={0} /> <Dot i={1} /> <Dot i={2} />
              </span>
              routing & retrieving…
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={onSubmit} className="flex items-end gap-2 pt-2">
        <textarea
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(input);
            }
          }}
          placeholder="Ask about decisions, code, workflows, docs…"
          className="max-h-40 resize-none"
        />
        <button type="submit" className="primary h-[42px] px-5" disabled={pending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

function Dot({ i }: { i: number }) {
  const reduce = useReducedMotion();
  return (
    <motion.span
      className="inline-block h-1.5 w-1.5 rounded-full bg-current"
      animate={reduce ? undefined : { opacity: [0.3, 1, 0.3] }}
      transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
    />
  );
}
