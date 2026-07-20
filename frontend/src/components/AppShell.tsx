// Protected layout: a glass sidebar + glass top bar over the animated
// background. The content area itself is transparent (NOT glass) so each page's
// GlassCards sit directly on the backdrop — never a blurred panel inside another
// blurred panel (design guardrail: no nested backdrop-filter).

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { BarChart3, Brain, MessageSquare, Sparkles, Upload as UploadIcon } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import ProjectSelector from "./ProjectSelector";

const NAV = [
  { to: "/chat", label: "Chat", Icon: MessageSquare },
  { to: "/memories", label: "Memories", Icon: Brain },
  { to: "/upload", label: "Upload", Icon: UploadIcon },
  { to: "/evaluation", label: "Evaluation", Icon: BarChart3 },
];

export default function AppShell() {
  const { email, logout } = useAuth();
  const location = useLocation();
  const reduce = useReducedMotion();

  return (
    <div className="grid h-full grid-cols-[248px_1fr] gap-4 p-4">
      {/* Sidebar */}
      <aside className="glass flex flex-col p-4">
        <div className="flex items-center gap-2.5 px-2 pb-6 pt-1 text-[1.05rem] font-bold">
          <Sparkles size={20} className="text-accent shrink-0" />
          <span className="brand-gradient">MemoryRAG</span>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className="relative flex items-center gap-3 rounded-xl px-3 py-2.5 font-medium transition-colors hover:bg-white/6"
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-xl"
                      style={{
                        background: "rgba(168,85,247,0.22)",
                        boxShadow:
                          "inset 0 1px 0 rgba(238,218,255,0.16), 0 0 20px rgba(168,85,247,0.18)",
                      }}
                      transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 420, damping: 34 }}
                    />
                  )}
                  <item.Icon
                    size={18}
                    className={`relative z-10 shrink-0 ${isActive ? "text-accent" : ""}`}
                  />
                  <span className={`relative z-10 ${isActive ? "text-fg" : "text-fg-muted"}`}>
                    {item.label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="text-eyebrow mt-auto px-2 pb-1">Adaptive Memory Routing</div>
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-col gap-4">
        <header className="glass flex h-16 items-center justify-between px-5">
          <ProjectSelector />
          <div className="flex items-center gap-3">
            <span className="text-fg-muted text-sm">{email}</span>
            <button type="button" className="ghost" onClick={logout}>
              Log out
            </button>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-auto pr-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={reduce ? false : { opacity: 0, y: 10 }}
              animate={reduce ? undefined : { opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
