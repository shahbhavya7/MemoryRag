# 📘 Phase 8 — Git Integration (Code Memory)

> A simple learning journal for Phase 8 of MemoryRAG. Plain, beginner-friendly
> language — meant to be pasted straight into Notion.

## TL;DR — what did we actually make?

We taught MemoryRAG to read a project's **git history** and turn it into
searchable memory. Point it at a local repo and it walks every commit, turns
each one (message + diff) into text, embeds it, and stores it in **code
memory** — plus **decision memory** when the commit message explains a *why*.
Each entry is tagged with the **commit hash**, so an answer can cite the exact
commit(s) it used.

Built with **GitPython**. We added a CLI *and* an endpoint to trigger it, and a
demo that ingests this very project's history and asks questions about it.

We verified it live: ingesting our 7 commits gave 14 code chunks + 2 decision
entries, and asking "what changed when adaptive memory routing was added?"
returned an accurate summary that **cited commit `135e7679`**.

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/services/git_ingest.py` | Walks a repo's commits and stores them into code/decision memory (has a CLI too) |
| `backend/api/ingest.py` | `POST /ingest/git` — the HTTP way to trigger ingestion |
| `backend/schemas.py` (added) | Request/response shapes for the ingest endpoint |
| `demo/demo_phase8.py` | Ingests THIS repo, asks about it, prints answers + cited commits |

For the deep, line-by-line version, see [`phases/phase8.md`](../phases/phase8.md).

---

## 🧠 New words explained super simply

- **Commit** — one saved change in git. Has a hash, a message, and a diff.
- **Diff** — the actual lines added/removed. The real "what changed" detail.
- **Commit hash** — the commit's unique id (e.g. `135e7679…`). We use it as the
  `source_ref` so citations point at an exact commit.
- **GitPython** — a Python library for reading a repo from code.
- **First commit** — has no parent, so we diff it against the "empty tree" to
  still capture its files.
- **"Why" commit** — a commit whose message explains a reason ("…because…",
  "we switched to…"). We store those in decision memory too.

---

## 🛠️ The setup story — what we ran, and how it went

1. **Installed GitPython** into the conda env and pinned it in
   `requirements.txt`.
2. **Wrote the ingest service.** For each commit: build "message + capped diff"
   text → chunk it → store each chunk in **code memory** with `source_ref =
   commit hash`. If the message looks like a decision, also store it in
   **decision memory**. All via the same `store_memory` from Phase 5.
3. **Added a CLI and an endpoint.** `python -m backend.services.git_ingest .`
   for the terminal, `POST /ingest/git` for HTTP — both call the same function.
4. **Wrote the demo.** It ingests this repo, then asks "in the code history,
   what changed when…" questions and prints the cited commit hashes.
5. **Verified live:**
   - Ingested 7 commits → **14 code chunks + 2 decision entries.**
   - "What changed when adaptive memory routing was added?" → routed to
     `['code', 'decision']`, accurate answer, **cited `135e7679`.**
   - "What changed with the multi-memory split?" → cited `24608e30`.
   - "What was done to add embeddings and vector search?" → cited `8b991fcf`.

---

## 🧩 The one thing that tripped us up (worth remembering)

At first every answer came back **"I don't know"** even though the right
commits were being retrieved. The cause: the server was running with a **tiny
`CONTEXT_TOKEN_BUDGET` (80)** left over from Phase 7 testing. Git diff chunks
are **big** (~800 tokens each), so a whole commit couldn't fit the context
slice and got dropped.

That's the **Phase 7 token budget working as designed**, not a Phase 8 bug. The
moment we ran with a normal budget (`2000`), the same questions produced rich,
correct, commit-cited answers.

**Lesson:** the size of what you store and the size of your context budget have
to match. Big memories (like diffs) need a bigger budget.

---

## 🧪 How to try it yourself

```bash
# make sure the budget is healthy for large git chunks
# (in .env: CONTEXT_TOKEN_BUDGET=1500  — or export it before starting)

# Terminal 1
./run.sh

# Terminal 2 — ingest this repo and ask about it
python demo/demo_phase8.py http://localhost:8010
```

Or ingest any repo from the terminal, no server needed:

```bash
set -a; source .env; set +a
python -m backend.services.git_ingest /path/to/some/repo --max-commits 20
```

Then ask via `POST /chat` something like *"in the code history, what changed
when X was added?"* and look at the `sources` — each `source_ref` is a commit
hash you can verify with `git show <hash>`.

---

## ✅ What to remember going forward

- **Git history is honest, free memory.** It already records what changed and
  often why — no hand-typing needed.
- **The commit hash is the perfect citation.** `source_ref = hash` means every
  answer points at a real, checkable commit.
- **One commit → two memories.** The diff is a *code* fact; the "why" message is
  a *decision*. Routing later picks whichever the question needs.
- **Reuse the write path.** New source, same `store_memory` — vectors and rows
  stay consistent with all the other memories.
- **Match memory size to budget.** Large chunks (diffs) need a larger
  `CONTEXT_TOKEN_BUDGET`, or the context builder will correctly drop them.
