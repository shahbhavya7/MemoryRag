# Phase 9 — The Frontend Dashboard (Beginner Notes)

This is our first **frontend** phase. Everything before now was a backend you
poked with curl or Swagger. Phase 9 builds a real web UI (React) that logs in,
talks to the FastAPI backend, and — the whole point — makes the **routing** and
**context engineering** *visible on screen*.

It's big, so we build it in sub-steps and get each one **rendering** before
adding the next (same discipline as the backend phases):

- **9a** — scaffold + auth + app shell + project selector ✅
- **9-design** — liquid-glass design system + restyle the shell ✅ (see below)
- **9b** — Chat page + routing-transparency panel ✅
- **9c** — Memories browser + Upload page ✅
- **9d** — Evaluation dashboard ✅

---

## 9a — Scaffold, Auth, App Shell, Project Selector

### What we built

1. **CORS on the backend** so the browser is *allowed* to call the API.
2. A **React + Vite + TypeScript** app in `frontend/`.
3. **Login + Register** pages that call the Phase 2 `/auth` endpoints and keep
   the JWT **in memory**.
4. A **protected app shell**: a sidebar (Chat / Memories / Upload / Evaluation)
   and a top bar (logged-in user + project selector).
5. A **project selector** backed by the `/projects` endpoints.

### New words used in this phase

- **Frontend / backend** — the frontend is the part that runs in the *browser*
  (what the user sees); the backend is the API + database we built earlier.
- **React** — a JavaScript library for building UIs out of reusable
  "components" (functions that return HTML-like markup called JSX).
- **Vite** — the dev server + build tool. `npm run dev` gives you a live-
  reloading site at `http://localhost:5173`.
- **TypeScript** — JavaScript with types. Catches "you passed the wrong shape"
  bugs before the app even runs.
- **Component** — one reusable piece of UI (e.g. `<ProjectSelector />`).
- **Props / state** — *props* are inputs passed into a component; *state* is
  data a component remembers and can change (via `useState`).
- **Context** — React's way to share state (like "the logged-in user") across
  many components without passing it through every level by hand.
- **Route / router** — maps a URL path (`/chat`) to which page component shows.
  We use `react-router-dom`.
- **CORS (Cross-Origin Resource Sharing)** — a browser security rule: a page on
  `localhost:5173` may not call an API on `localhost:8010` *unless the API says
  it's allowed*. The backend must opt-in. **Nothing works until this is done.**
- **JWT / Bearer token** — the login token from Phase 2. We send it on every
  request as an `Authorization: Bearer <token>` header to prove who we are.

### The CORS change (backend)

In `backend/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Before a "real" POST, the browser quietly sends an `OPTIONS` **preflight** to
ask "am I allowed?". This middleware answers "yes, from 5173." Without it, the
browser blocks the call before your code ever sees it — the classic "it works
in curl but not in the browser" trap.

### The frontend files (one line each)

| File | What it does |
|---|---|
| `src/api/client.ts` | `fetch` wrapper: attaches the Bearer token, turns errors into a clean `ApiError`, exposes typed `api.login/register/listProjects/createProject` |
| `src/api/types.ts` | TypeScript shapes mirroring the backend schemas (User, Token, Project, the 5 memory types) |
| `src/auth/AuthContext.tsx` | Holds token + email **in memory**; `login/register/logout`; `isAuthenticated` |
| `src/project/ProjectContext.tsx` | Loads `/projects`, tracks the selected project, `createProject` |
| `src/components/ProtectedRoute.tsx` | No token → redirect to `/login` |
| `src/components/AppShell.tsx` | Sidebar + top bar + `<Outlet/>` (where the page renders) |
| `src/components/ProjectSelector.tsx` | The top-bar dropdown + inline "new project" form |
| `src/pages/LoginPage.tsx` / `RegisterPage.tsx` | The auth forms |
| `src/pages/*Page.tsx` | The four feature pages (placeholders until 9b–9d) |
| `src/App.tsx` | The route table (public auth routes + protected shell routes) |
| `src/main.tsx` | Mounts the app, wraps it in Router + Auth + Project providers |
| `src/index.css` | The whole look — one hand-written stylesheet, no framework |

### Why the token is "in memory only"

The prompt asked for the JWT in memory/context, **not** localStorage, for now.
So we keep it in a module variable in `client.ts` (mirrored by React state in
`AuthContext`). Trade-off: **refreshing the page logs you out.** That's the
expected behavior for this phase — persisting login safely (refresh tokens,
httpOnly cookies) is a later concern.

### How the request flow works

1. You submit the login form → `AuthContext.login()` calls `api.login()`.
2. The backend returns `{access_token}`.
3. `setAuthToken(token)` stashes it in the API client, and React state flips
   `isAuthenticated` to true.
4. `ProtectedRoute` now lets you into the shell; `ProjectContext` auto-loads
   your projects.
5. Every later call (e.g. `listProjects`) automatically gets the
   `Authorization: Bearer <token>` header from the client wrapper.

### How we verified it (live)

The build passed TypeScript (`npm run build` → 37 modules transformed), and we
drove the exact browser flow with curl against a fresh backend:

- **CORS preflight** (`OPTIONS /auth/register` with `Origin: localhost:5173`)
  → `200` with `access-control-allow-origin: http://localhost:5173` ✅
- `POST /auth/register` → `201` ✅
- `POST /auth/login` → `200` + a 119-char token ✅
- `GET /projects` with the Bearer token → `200` ✅
- `POST /projects` → `201` (created "Demo Workspace") ✅
- `GET /projects` **without** a token → `401` ✅ (the guard works)
- Vite dev server served the app and transformed every module with no errors ✅

### The gotcha we hit

`React.FormEvent` was used without importing React. With React 19's automatic
JSX runtime, `React` isn't in scope by default, so TypeScript couldn't find it.
Fix: import the type by name — `import { useState, type FormEvent } from "react"`
— and use `FormEvent` directly. Lesson: in modern React you import the specific
hooks/types you use; there's no implicit global `React`.

### Try it yourself

```bash
# Terminal 1 — backend (repo root)
./run.sh

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 → Register → you land in the shell. Create a couple
of projects in the top bar and switch between them; the active project name
shows on each (still empty) feature page, proving project scoping is wired up.

---

## 9-design — The Liquid-Glass Design System

### What we built

A cohesive **glassmorphism** design system and a restyle of the existing shell
(sidebar, top bar, login/register) to use it. **No new features** — this is a
look-and-feel pass that every later page (9b–9d) inherits.

- Installed + configured **Tailwind CSS v4** (`@tailwindcss/vite`) and **Framer
  Motion**.
- One reusable **`<GlassPanel>` / `<GlassCard>`** primitive.
- A dark **animated aurora background** (drifting blurred blobs) — glass needs
  something behind it to blur.
- A restrained **2-accent palette** + Inter typography.
- Enforced guardrails (contrast, blur cost, motion restraint, fallback).
- Full spec written in [`frontend/DESIGN.md`](../frontend/DESIGN.md).

### New words used in this phase

- **Glassmorphism / liquid glass** — a UI style where panels look like frosted
  glass: semi-transparent, blurring whatever is behind them, with a bright hairline
  edge and soft shadow.
- **`backdrop-filter: blur()`** — the CSS that actually blurs *what's behind* an
  element (as opposed to `filter: blur()`, which blurs the element itself). This
  is what makes glass "glass."
- **Design token** — a named value (a color, a radius, a blur amount) defined
  once and reused, so the whole app changes consistently from one place.
- **Tailwind CSS** — a utility-class styling system (`flex`, `p-4`, `text-fg`).
  v4 configures its theme in CSS via `@theme`, no `tailwind.config.js` needed.
- **Framer Motion** — a React animation library; you make an element animated by
  using `<motion.div>` with `initial` / `animate` / `exit` props.
- **`prefers-reduced-motion`** — an OS accessibility setting; we detect it and
  switch off non-essential animation.
- **WCAG AA** — an accessibility contrast standard: text must be clearly legible
  against its background. Our guardrail.

### The single most important idea: one primitive

Everything glass comes from **one** `.glass` class in `index.css` — the only
place `backdrop-filter` is defined — wrapped by **one** React component,
`<GlassPanel>`. Change the recipe once, the whole app changes. This is what the
"Consistency" guardrail means in practice: no page invents its own panel.

### Why a *dark* translucent glass (the contrast trick)

The classic glass look is "8–14% white over a dark background." That looks great
until text sits over a *bright* part of the background and washes out. Our fix:
the glass body is a **dark** translucent tint (`rgba(17,19,31,0.45)`) with a
**light diagonal sheen** painted on top. The dark base guarantees near-white
text stays readable no matter what's behind it; the sheen + a 1px inset
highlight still give the frosted, light-edged glass look. Best of both.

### The guardrails we enforced (and why)

1. **Contrast** — body text is near-white (`--fg`) on dark glass → passes AA
   even over the brightest blob. No gray body text on glass.
2. **Blur is expensive** — `backdrop-filter` only on a few large panels
   (sidebar, top bar, page cards). Buttons/badges/inputs use plain translucent
   fills. And **no nested blur**: the area between the glass shell and the page
   cards is transparent, so a card never sits inside another blurred panel.
3. **Motion restraint** — Framer Motion for route transitions (fade + rise),
   panel mount, and hover lifts; 150–400ms, gentle easing, no bounce. The only
   infinite animation is the slow background drift. All disabled under
   `prefers-reduced-motion`.
4. **Fallback** — `@supports not (backdrop-filter…)` makes panels near-opaque so
   the UI degrades to *readable* instead of *transparent-mush*.

### Files

| File | What it does |
|---|---|
| `src/index.css` | Tokens (`:root` + `@theme`), the `.glass` primitive + fallback, the aurora keyframes, reduced-motion rules |
| `src/components/GlassPanel.tsx` | `<GlassPanel>` / `<GlassCard>` — the one glass surface, with a Framer-Motion mount animation |
| `src/components/Background.tsx` | The fixed animated aurora backdrop |
| `vite.config.ts` | Adds the Tailwind v4 Vite plugin |
| `frontend/DESIGN.md` | The full written spec |
| `AppShell` / `Login` / `Register` / etc. | Restyled to use the glass system |

### How we verified it

`npm run build` compiled cleanly (441 modules). We confirmed the **compiled
CSS** actually contains the system: `.glass`, `backdrop-filter`,
`saturate(160%)`, the `bg-aurora` layer, the `drift1` keyframes, the
`@supports not` fallback, and the `prefers-reduced-motion` block — all present.
The dev server booted and served the restyled app.

### Try it yourself

Run the app (`./run.sh` + `npm run dev`) and open http://localhost:5173. You
should see: the login card as frosted glass floating over a slowly drifting
aurora; after logging in, a glass sidebar + top bar; smooth fade-and-rise when
switching tabs; and fully readable text everywhere. Toggle "Reduce motion" in
your OS accessibility settings and reload — the drift and transitions stop.

---

## 9b — Chat + Routing Transparency

### What we built

The Chat page — a message thread + input that calls `POST /chat` (the Phase 6
routing graph), scoped to the selected project. **The whole point** is making
the routing *visible*: every answer shows which memory type(s) the router picked
as prominent animated **badges**, plus a **routing-transparency panel** with the
retrieved sources (and their scores) and the Phase 7 **token breakdown**
(kept vs. dropped) from `GET /context-trace/{message_id}`.

### New words used in this phase

- **Message thread** — the running list of your questions + the assistant's
  answers, like any chat app.
- **Badge** — a small pill label. Here, one per chosen memory type, each in that
  type's own color.
- **Routing transparency** — showing *why* an answer looks the way it does: what
  memory was searched, what chunks came back and how well they matched (score),
  and how the token budget was spent.
- **Context trace** — the Phase 7 "receipt" for one answer (kept vs. dropped
  chunks + token counts). We fetch it right after each answer.

### How it flows

1. You type a question → `POST /chat {project_id, message}`.
2. The response has `answer`, `memory_types` (the router's pick),
   `sources`, and a `message_id`.
3. We render the answer in a glass card with the memory-type **badges animating
   in** at the top.
4. Using the `message_id`, we then fetch `GET /context-trace/{message_id}` and
   fill in the token breakdown + kept/dropped chunk list. While it loads, the
   panel shows a **glass shimmer** (no spinner-on-white).

### Design decisions (staying within the system)

- **Each answer is one `GlassPanel`** — one `backdrop-filter` per answer. User
  messages are plain translucent bubbles (cheap), and the transparency details
  inside the answer card use plain translucent sub-rows — so we never nest a
  blurred panel inside another (the guardrail).
- **Badges are the loud part**, and they're cheap (no blur) — each tinted with
  its memory type's color and animated in with a tiny stagger, so the routing
  decision is the first thing your eye lands on.
- Messages **rise + fade in**; a three-dot "routing & retrieving…" indicator
  shows while waiting. All motion respects reduced-motion.
- New words / colors come from `lib/memoryTypes.ts` — one source of truth for
  each type's label + color + emoji, matching the `--mt-*` tokens.

### Files

| File | What it does |
|---|---|
| `src/pages/ChatPage.tsx` | The thread, input, send flow, and per-answer glass cards |
| `src/components/MemoryBadge.tsx` | The animated, per-type tinted badge (the centerpiece) |
| `src/components/RoutingTransparency.tsx` | Token-budget bar + kept/dropped source list |
| `src/lib/memoryTypes.ts` | Per-type label/color/emoji (matches the CSS tokens) |
| `src/api/client.ts` / `types.ts` | `sendChat` + `getContextTrace` and their types |

### How we verified it (live)

We seeded the five memory types and drove the exact endpoints the page calls:

- "Why did we choose PostgreSQL over MongoDB?" → routed **`['decision']`**,
  4 sources, trace `total 767 / 1500`, 4 kept / 0 dropped.
- "How do we deploy the backend?" → routed **`['workflow']`**, 3 sources.
- "What does the slugify function do?" → routed **`['code']`**, and the trace
  showed **2 kept / 2 dropped** — so the panel really does show chunks getting
  dropped when the budget is tight.

Different questions → different badges → different sources: exactly the proof
this page is meant to give. The build compiled cleanly and the dev server served
the page with no transform errors.

### Try it yourself

Run the stack (`./run.sh` + `npm run dev`), seed some memories
(`python demo/seed_phase6.py http://localhost:8010`), then on the Chat page ask
the suggested questions. Watch the badge + sources change per answer, and expand
the token breakdown to see kept vs. dropped. (Use a healthy
`CONTEXT_TOKEN_BUDGET` ~1500 so answers are grounded — the Phase 8 lesson.)

---

## 9c — Memories Browser + Upload

### What we built

Two pages, plus one new backend endpoint:

- **Upload** — a glass form to add a typed memory (`POST /memories`) and a
  second form to upload a plain-text document (`POST /documents/upload`). Success
  and error feedback are **inline glass toasts**, not browser alerts.
- **Memories** — a responsive grid of memory cards, **filterable by type**, each
  showing content + `source_ref` + `created_at`. Changing the filter **re-lays
  out the grid with Framer Motion layout animations** (cards glide/fade as they
  come and go).
- **Backend:** a new `GET /memories` list endpoint (with an optional
  `?memory_type=` filter), since one didn't exist yet.

### New words used in this phase

- **Toast** — a small, temporary notification that slides in (here, in glass)
  and auto-dismisses. Friendlier than a blocking `alert()` popup.
- **Layout animation** — Framer Motion watches an element's position/size and
  animates it smoothly when it *changes* (e.g. cards reflowing when you filter).
  You opt in with the `layout` prop.
- **`AnimatePresence`** — lets elements animate *out* when they're removed from
  the list (not just in).
- **Multipart / FormData** — how a browser uploads a file: the request body is
  `FormData` with the file attached, and the browser sets the content type.

### The one design decision worth calling out

A grid can hold *many* cards, and `backdrop-filter` (real blur) is expensive —
our own guardrail says "blur only on a few large panels." So memory cards use a
new **`lite` glass** variant: the exact glass *look* (cool sheen, hairline,
shadow, radius) but **no `backdrop-filter`**, with a slightly higher base opacity
so text stays readable without the blur. Singular panels still get real blur;
grids get the cheap look-alike. This is the kind of principled call that keeps a
glass UI fast instead of janky.

### Files

| File | What it does |
|---|---|
| `src/pages/UploadPage.tsx` | Add-memory form + document-upload form + toasts |
| `src/pages/MemoriesPage.tsx` | Filter chips + animated grid of memory cards |
| `src/components/Toast.tsx` | `useToasts()` hook + `<ToastStack>` (glass toasts) |
| `src/components/GlassPanel.tsx` | Added the `lite` (no-blur) variant |
| `backend/api/memories.py` | New `GET /memories` list endpoint (+ type filter) |

### How we verified it (live)

- `GET /memories` → 200 with all memories grouped by type; `?memory_type=decision`
  → only decisions; `?memory_type=bogus` → **400** (clear error).
- `POST /memories` → 201 (created a "trunk-based development" decision).
- `POST /documents/upload` (multipart, exactly as the UI sends it) → 201,
  `chunks_created: 1`.
- All three pages transformed in the dev server with no errors.

### Try it yourself

On **Upload**, add a decision (e.g. "We decided to adopt trunk-based
development") → a green glass toast confirms it. Go to **Memories**, click the
**Decision** filter → the grid animates down to just decisions and your new card
is there.

---

## 9d — Evaluation Dashboard

### What we built

- **Backend:** a new `POST /evaluation/run` endpoint that runs the Phase 7
  routing gold set through the classifier on demand and returns overall accuracy,
  a per-memory-type breakdown, and each question's expected-vs-predicted result.
  (The gold set moved to `backend/eval_data.py` so the CLI eval and this endpoint
  share **one** source of truth.)
- **Frontend:** an Evaluation page that renders it in glass — overall accuracy as
  an **animated count-up**, a **per-type breakdown with bars that grow** to their
  values, and a **table** of every question with mismatches **highlighted in the
  accent color**. The "Run evaluation" button shows a **glass shimmer** while it
  works (no spinner-on-white).

### New words used in this phase

- **On-demand endpoint** — work that runs only when you ask (a button press),
  not on every page load. This one makes real LLM calls, so it's deliberately
  behind a button.
- **Count-up animation** — a number that animates from 0 to its final value,
  drawing the eye to the headline metric.
- **Gold set** — the fixed list of questions with human-decided correct answers
  (from Phase 7). Accuracy = how many the router got right.

### Files

| File | What it does |
|---|---|
| `backend/eval_data.py` | The shared gold set (used by CLI + endpoint) |
| `backend/api/evaluation.py` | `POST /evaluation/run` — scores routing, returns JSON |
| `src/pages/EvaluationPage.tsx` | Count-up stat, per-type bars, mismatch table |
| `demo/eval_phase7.py` | Refactored to import the shared gold set |

### How we verified it (live)

`POST /evaluation/run` → 200, **accuracy 100% (10/10)**, every type 2/2, zero
mismatches — returning exactly the shape the dashboard renders (a number for the
count-up, `per_type` for the bars, `results` for the table). The build compiled
cleanly and the page transformed with no errors.

### Try it yourself

On **Evaluation**, click **Run evaluation**. After a few seconds (it makes one
classifier call per question) the accuracy count-up animates in, the per-type
bars grow, and the table fills — any misroute is highlighted. Switch
`CLASSIFIER_PROMPT_VERSION` to `v1` in `.env`, restart the backend, and re-run to
compare prompt versions as a number.
