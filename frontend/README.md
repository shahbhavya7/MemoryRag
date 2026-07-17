# MemoryRAG Frontend

A React + Vite + TypeScript dashboard for the MemoryRAG backend. The whole
point of this UI is to make **Adaptive Memory Routing** and **context
engineering** *visible* — you can watch which memory type the router picks and
what context an answer was built from.

Built phase-by-phase:

- **9a** — scaffold, JWT auth (login/register), protected app shell, project selector ✅
- **9-design** — liquid-glass design system (cyan→blue) — see [DESIGN.md](DESIGN.md) ✅
- **9b** — Chat page + routing-transparency panel ✅
- **9c** — Memories browser + Upload page ✅
- **9d** — Evaluation dashboard ✅

## Prerequisites

- Node.js + npm (installed via `brew install node`).
- The MemoryRAG backend running (see the repo root `README.md` / `run.sh`).
  CORS is already enabled on the backend for `http://localhost:5173`.

## Running it

```bash
# 1. Start the backend (from the repo root). Default port is 8010.
./run.sh

# 2. Start the frontend dev server (from this folder).
cd frontend
npm install        # first time only
npm run dev        # serves http://localhost:5173
```

Open http://localhost:5173, register or log in, and you're in the app shell.

## Pointing at a different backend port

The frontend talks to `http://localhost:8010` by default. To use another port,
set `VITE_API_URL` when starting the dev server:

```bash
VITE_API_URL=http://localhost:8020 npm run dev
```

## Notes

- The JWT is kept **in memory only** (React context) — deliberately *not*
  localStorage for now, so refreshing the page logs you out. That's expected.
- Styling is a single hand-written stylesheet (`src/index.css`) — no CSS
  framework — including the per-memory-type accent colors used by the routing
  badges from 9b onward.

## Structure

```
src/
├── api/           # fetch wrapper (attaches the Bearer token) + shared types
├── auth/          # AuthContext — token/email in memory, login/register/logout
├── project/       # ProjectContext — project list + current selection
├── lib/           # memoryTypes — per-type label/color/emoji (matches CSS tokens)
├── components/    # GlassPanel, Background, AppShell, MemoryBadge, RoutingTransparency, Toast, …
└── pages/         # Login, Register, Chat, Memories, Upload, Evaluation
```

## Seeing it populated

The Chat and Memories pages need data. With the backend running, seed the five
memory types:

```bash
python demo/seed_phase6.py http://localhost:8010
```

Then the Chat suggestions return grounded answers, and the Memories browser has
cards to filter. Keep `CONTEXT_TOKEN_BUDGET` ~1500 for grounded chat answers.
