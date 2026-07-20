# 📘 Phase 9 The Frontend Dashboard

> A simple learning journal for Phase 9 of MemoryRAG. Plain, beginner-friendly
> language meant to be pasted straight into Notion. Built in sub-steps
> (9a → 9d); this note grows as each lands.

## TL;DR what is Phase 9?

Our first **web UI**. Until now MemoryRAG was a backend you talked to with curl
or Swagger. Phase 9 builds a real **React dashboard** that logs in and the
whole point makes the **routing** (which memory the system picks) and the
**context engineering** (what an answer was built from) *visible on screen*.

Because it's large, we build it in four sub-steps and get each one **rendering
before adding the next**:

- **9a** scaffold + login/register + app shell + project selector ✅
- **9-design** liquid-glass design system + restyle the shell ✅
- **9b** Chat page + routing transparency ✅
- **9c** Memories browser + Upload ✅
- **9d** Evaluation dashboard ✅

---

## 9a Scaffold, Auth, App Shell, Project Selector ✅

### What we made

A React + Vite + TypeScript app in `frontend/` that you can **log into** and
that shows a proper **app shell** (sidebar + top bar) with a working **project
selector**. The four feature tabs exist and route, but are empty on purpose —
they get filled in 9b–9d.

### New words, super simply

- **Frontend** the part that runs in your browser (what you see and click).
- **React** build the UI from reusable "components".
- **Vite** the tool that runs the dev site at `localhost:5173` and rebuilds
  instantly as you edit.
- **TypeScript** JavaScript with types, so mistakes get caught early.
- **Context** React's "shared box" for state (like the logged-in user) that
  any component can read.
- **Router** decides which page to show for a URL like `/chat`.
- **CORS** a browser safety rule. A page on port 5173 can't call an API on
  port 8010 **unless the API explicitly allows it**. We turned that on first —
  nothing works without it.
- **JWT / Bearer token** the login token from Phase 2, sent on every request
  to prove who you are.

### The story what we did, and how it went

1. **Turned on CORS** in the backend (`main.py`) for `http://localhost:5173`.
   This is step zero skip it and every browser call silently fails.
2. **Installed Node** (`brew install node`) since it wasn't on the machine, then
   scaffolded the app with `npm create vite`.
3. **Built the auth flow.** Login/Register pages call `/auth/login` and
   `/auth/register`; the returned JWT is stored **in memory** (not localStorage,
   by design) and auto-attached as a Bearer token on every later request.
4. **Built the app shell.** A sidebar (Chat / Memories / Upload / Evaluation)
   and a top bar showing the user's email + a project dropdown. A
   `ProtectedRoute` bounces you to login if you have no token.
5. **Wired the project selector** to the `/projects` endpoints list, switch,
   and create projects right from the top bar.

### How we proved it works

The TypeScript build passed cleanly, and we replayed the exact browser steps
with curl against a fresh backend:

- CORS preflight from `localhost:5173` → allowed ✅
- register → login → got a token ✅
- list projects (with token) → OK; **without token → 401** ✅
- create a project → created ✅
- the Vite dev server served the app and compiled every file with no errors ✅

### The one thing that tripped us up

We wrote `React.FormEvent` but never imported `React`. Modern React (v19)
doesn't put `React` in scope automatically, so TypeScript complained. Fix:
import the exact thing you need `import { useState, type FormEvent } from
"react"`. **Lesson:** in modern React you import specific hooks/types; there's
no magic global `React`.

### Heads-up for later phases

- **Refreshing the page logs you out** that's expected, because the token is
  in memory only for now.
- For **9b (chat)** you'll want the backend on a **healthy
  `CONTEXT_TOKEN_BUDGET`** (e.g. 1500), same lesson as Phase 8 big chunks need
  room or the answer says "I don't know."

### Try it yourself

```bash
# Terminal 1 backend
./run.sh

# Terminal 2 frontend
cd frontend && npm install && npm run dev
# open http://localhost:5173
```

Register, land in the shell, create two projects, switch between them, and watch
the active project name update on each page. That's 9a proven.

---

## 9-design The Liquid-Glass Design System ✅

### What we made

A cohesive **frosted-glass** look for the whole app, and we restyled the
existing shell + auth pages to use it. This was a *design* pass no new
features so every page we build next (9b–9d) automatically looks consistent.

### New words, super simply

- **Glassmorphism / liquid glass** panels that look like frosted glass:
  see-through, blurring whatever is behind them, with a bright thin edge.
- **`backdrop-filter: blur()`** the CSS that blurs *what's behind* an element.
  This is the magic that makes glass look like glass.
- **Design token** a value (color, radius, blur) named once and reused, so the
  whole app stays consistent and is easy to change.
- **Tailwind** style with small utility classes (`flex`, `p-4`, `text-fg`).
- **Framer Motion** makes React elements animate (fade, rise, scale).
- **`prefers-reduced-motion`** an OS setting for people who don't want
  animation; we respect it and turn drift/transitions off.

### The story

1. Installed **Tailwind CSS v4** and **Framer Motion**.
2. Wrote **one** glass recipe (`.glass` in `index.css`) and **one** React
   wrapper (`<GlassPanel>`). Everything glass uses these change once, changes
   everywhere.
3. Added a dark **animated aurora background** slowly drifting blurred color
   blobs. Glass needs something behind it to blur; a flat background would make
   the whole effect pointless.
4. Restyled the sidebar, top bar, and login/register into glass, with smooth
   fade-and-rise transitions between tabs.
5. Wrote the full spec in `frontend/DESIGN.md`.

### The big lesson: contrast beats "pretty"

The classic glass look (faint white panel over dark) looks slick but text can
wash out over bright spots. So our glass body is actually a **dark** see-through
tint with a **light sheen** on top the dark base keeps near-white text
readable no matter what's behind it, while still looking frosted. **Readable
first, pretty second** that's the guardrail that separates a premium UI from a
"vibe-coded" one.

Other guardrails we stuck to: blur only on a few big panels (never nested,
never on tiny elements), gentle short animations (150–400ms, no bounce, one
slow ambient loop), and a solid fallback if a browser can't do `backdrop-filter`.

### How we proved it

The build compiled cleanly, and we checked the **compiled CSS** really contains
the glass system `.glass`, `backdrop-filter`, the aurora background, the drift
animation, the no-support fallback, and the reduced-motion rules were all there.
The dev server served the restyled app.

### Try it yourself

Run `./run.sh` + `npm run dev`, open http://localhost:5173: a frosted login card
over a drifting aurora, a glass sidebar/top bar after login, smooth tab
transitions, readable text everywhere. Turn on "Reduce motion" in your OS and
reload the movement stops.

---

## 9b Chat + Routing Transparency ✅

### What we made

The Chat page the heart of the whole UI. You ask a question, it goes to the
Phase 6 routing graph (`POST /chat`), and the answer comes back **showing its
work**: which memory type(s) the router picked (as bright animated badges), the
source chunks it used with match scores, and how the token budget was spent
(kept vs. dropped), pulled from the Phase 7 context trace.

### New words, super simply

- **Message thread** the back-and-forth list of questions and answers.
- **Badge** a little colored pill; here, one per memory type the router chose.
- **Routing transparency** the "show your work" panel: what memory was
  searched, what came back and how well it matched, and how many tokens each
  piece used (and whether it was kept or dropped).

### The story

1. Ask a question → the app calls `/chat`, scoped to the selected project.
2. The answer appears in a glass card with the **memory-type badges animating
   in** so the routing decision is the first thing you notice.
3. The app then fetches the **context trace** for that answer and fills in a
   token-budget bar + a list of the retrieved chunks (kept ones bright, dropped
   ones dimmed with a "dropped" tag). A glass **shimmer** shows while it loads.

### How we proved it

We seeded the five memory types and asked three questions:
- decision question → badge **Decision**, 4 sources;
- workflow question → badge **Workflow**, 3 sources;
- code question → badge **Code**, and the trace showed **2 kept / 2 dropped**.

Different question → different badge → different sources → visible kept/dropped.
That *is* the point of the page, and it works.

### The lesson

**Make the system explain itself, visually.** The backend already knew which
memory it used and what it kept 9b just surfaces it so a human sees the routing
and context engineering at a glance instead of reading JSON. A colored, animated
badge does more to explain "adaptive memory routing" than a paragraph could.

---

## 9c Memories Browser + Upload ✅

### What we made

Two pages: **Upload** (add a typed memory, or upload a text document) and
**Memories** (browse everything stored, filter by type). Plus a new backend
`GET /memories` list endpoint to feed the browser.

### New words, super simply

- **Toast** a little pop-in notification that fades away by itself. We use
  glass ones instead of the browser's ugly `alert()` box.
- **Layout animation** Framer Motion smoothly slides cards to their new spots
  when the list changes (e.g. when you filter). You just add a `layout` prop.
- **FormData** how a file gets uploaded from the browser.

### The story + the smart call

Upload has two glass forms; saving shows a green toast, failing shows a red one.
Memories shows a grid of cards you can filter by type, and the cards **animate**
into their new positions when you filter.

The smart decision: a grid can have lots of cards, and real glass blur is
expensive. So grid cards use a **`lite` glass** same frosted *look*, but no
blur while big single panels keep the real blur. That's how you keep a glass
UI smooth instead of laggy. (Our own guardrail: blur only on a few large
panels.)

### How we proved it

Listed memories (grouped by type), filtered to just decisions, created a new
decision (201), and uploaded a text doc (201, 1 chunk) all through the exact
endpoints the pages call. A bad filter type correctly returned 400.

---

## 9d Evaluation Dashboard ✅

### What we made

A page that **scores the router** on demand and shows it beautifully: click
**Run evaluation** → the backend runs the Phase 7 gold set through the classifier
and returns accuracy; the page animates a big **count-up** percentage, grows a
**bar per memory type**, and lists every question with any **misroute
highlighted**.

### New words, super simply

- **On-demand** it only runs when you click the button (it costs real LLM
  calls), not automatically.
- **Count-up** the headline number animates from 0 up to its value.
- **Gold set** the fixed list of questions with known-right answers; accuracy
  is how many the router got right.

### The story

We put the gold set in one shared file (`backend/eval_data.py`) so the old CLI
eval and the new endpoint can't drift apart. The endpoint returns accuracy +
per-type breakdown + per-question results. The page turns that into a count-up
stat, animated bars, and a mismatch-highlighted table, with a glass shimmer while
it runs.

### How we proved it

`POST /evaluation/run` → 100% (10/10), every type 2/2, no mismatches exactly
the shape the dashboard draws.

### The lesson

**A metric you can run with one click gets run.** Turning the CLI eval into a
button with animated results makes "is the router any good?" something you
actually check and comparing prompt v1 vs v2 becomes a visible number, not a
gut feeling.

---

## ✅ What to remember going forward

- **CORS first, always.** A browser app is blocked from your API until the API
  says "this origin is allowed." (Vite can fall back to 5174/5175 if 5173 is
  busy we allow those too.)
- **One glass primitive.** All frosted surfaces come from a single `.glass`
  recipe + `<GlassPanel>` that's what keeps the UI consistent.
- **Readable over pretty.** Dark-tinted glass keeps text legible; never gray
  body text on glass.
- **Show the routing.** Badges + the transparency panel turn the invisible
  backend decision into the visible centerpiece.
- **The token rides on every request.** One `fetch` wrapper attaches
  `Authorization: Bearer <token>` so no page has to think about it.
- **Context = shared state.** Auth and project selection live in React context
  so the whole app sees the same "who am I / which project" without prop-drilling.
- **Build rendering-first, sub-step by sub-step** same phase-wise discipline
  as the backend.
