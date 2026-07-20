# Phase 8 Git Integration → Code Memory (Beginner Notes)

## What are we even building in this phase?

Until now, every memory in the system was something a human typed in by hand
(via `POST /memories` or a seed script). That's fine for a demo, but a real
codebase already has a huge, honest record of *what changed and why*: its
**git history**.

Phase 8 connects that history to the system. You point MemoryRAG at a local git
repository, and it:

1. Walks the **commit log** (newest first).
2. For each commit, builds a text document from the **commit message + its
   diff** (the actual code changes).
3. **Embeds** that text and stores it in **code memory**.
4. If the commit message reads like it's explaining a *decision* ("we switched
   to X because…"), it **also** stores the message in **decision memory**.
5. Records every entry in the `memories` table with `source_ref` set to the
   **commit hash** so any answer can cite the exact commit it came from.

Nothing about *storage* is new we reuse the same `store_memory` writer from
Phase 5. Phase 8 is a new **source** of memories, not a new storage path.

---

## 1. New words used in this phase

- **Git commit** one saved change in a repo's history. Has a unique **hash**
  (like `135e7679…`), an author, a date, a **message**, and a **diff**.
- **Diff** the exact lines added/removed by a commit. This is where the real
  "what changed" detail lives (the message is just a summary).
- **Commit hash (SHA)** the unique id of a commit. We use it as the
  `source_ref`, so citations point at a specific commit you can `git show`.
- **GitPython** a Python library that lets us read a repo (commits, diffs,
  branches) without shelling out to the `git` command.
- **Parent commit** the commit right before this one. A diff is "this commit
  vs. its parent." The very first commit has *no* parent, so we diff it against
  the **empty tree** instead.
- **Ingestion** the whole process of reading an external source (here, git)
  and loading it into our memory system.

---

## 2. The folder structure now

```
backend/
├── api/
│   └── ingest.py          # NEW: POST /ingest/git endpoint
├── services/              # NEW package for "do a job" modules
│   ├── __init__.py
│   └── git_ingest.py      # NEW: the git-walking + storing logic (+ a CLI)
└── ... (everything from Phases 1–7 unchanged)

demo/
└── demo_phase8.py         # NEW: ingest this repo, then ask about it
```

Why a new `services/` package? The suggested folder structure in the project
brief has one. It's the natural home for "a task the app performs" that isn't
an HTTP route or a database model like ingesting git history. The endpoint
(`api/ingest.py`) stays thin and just calls the service.

---

## 3. `backend/services/git_ingest.py` line by line

### The knobs at the top

```python
MAX_DIFF_CHARS = 6000
```
Diffs can be *enormous* (a lockfile change can be tens of thousands of lines).
Embedding megabytes of patch is slow and low-value, so we keep at most 6000
characters of diff per commit a readable, representative slice.

```python
WHY_MARKERS = ("because", "reason", "in order to", "so that", "to avoid",
               "instead of", "rather than", "decided", "decision", "chose",
               "choose", "switch", "migrate", ... "why")
```
A cheap keyword list. If a commit message contains any of these, we treat it as
explaining a *decision* and also file it under decision memory. It's a
heuristic, not magic the project's "future work" is to replace it with a real
classifier. (Note: it's a substring match, so a plain title like "Phase 6:
Implement Adaptive Memory Routing" doesn't trip it, but "…because we need
transactions" does.)

### Reading one commit's diff

```python
def _commit_diff_text(commit):
    if commit.parents:
        diffs = commit.parents[0].diff(commit, create_patch=True)
    else:
        diffs = commit.diff(git.NULL_TREE, create_patch=True)
```
- `create_patch=True` tells GitPython to include the actual patch text (the
  +/- lines), not just the list of changed files.
- The `if commit.parents` branch handles the **first commit** specially: it has
  no parent, so we diff against `git.NULL_TREE` (the empty tree) otherwise its
  files would never show up.

```python
    for d in diffs:
        path = d.b_path or d.a_path or "?"
        files.append(path)
        patch = d.diff.decode("utf-8", errors="replace") ...
```
For each changed file we grab its path and its patch bytes, decoding to text
(with `errors="replace"` so a binary/odd file can't crash the whole ingest).

```python
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n...[diff truncated]..."
```
The safety cap from above.

### Turning a commit into an embeddable document

```python
def _commit_document(commit, files, diff_text):
    return (
        f"Commit {short} by {commit.author.name} on {date}\n"
        f"Message: {message}\n"
        f"Files changed: {file_list}\n\n"
        f"Diff:\n{diff_text}"
    )
```
This is the text we actually embed. The **message comes first** on purpose —
it's the highest-signal part, so even the first chunk (see below) is meaningful.

### The main loop

```python
def ingest_git_repo(db, repo_path, max_commits=None, branch=None):
    repo = git.Repo(repo_path)            # raises if not a git repo -> we turn that into a ValueError
    commits = list(repo.iter_commits(rev=branch, max_count=max_commits))
```
Open the repo and list its commits (optionally limited to the newest N, or a
specific branch).

```python
    for commit in commits:
        ...
        chunks = chunk_text(document) or [document]
        for chunk in chunks:
            store_memory(db, "code", chunk, source_ref=sha)
            code_chunks_stored += 1
```
- We reuse the Phase 3 `chunk_text` to split a long commit document into
  ~500-word pieces (a big diff becomes 2–3 chunks). `or [document]` guards the
  edge case where chunking returns nothing.
- Each chunk goes into **code memory** via the shared `store_memory` which
  gives it a Postgres row *and* a Pinecone vector tagged with the commit hash.

```python
        if _looks_like_decision(commit.message):
            store_memory(db, "decision",
                         f"Decision recorded in commit {short}: {message}",
                         source_ref=sha)
```
"Why" commits *also* get their message stored in **decision memory**. We store
the message (the reasoning), not the whole diff a decision is about *why*, not
line-by-line *what*.

The function returns a summary dict (counts + a per-commit list) so the CLI,
the endpoint, and the demo can all show exactly what happened.

### The CLI

```python
if __name__ == "__main__":
    _main()
```
`_main()` uses `argparse` to accept `<repo_path> [--max-commits N] [--branch NAME]`,
seeds the memory types, runs the ingest, and prints a summary. So you can ingest
a repo **without starting the server**:

```bash
python -m backend.services.git_ingest . --max-commits 5
```

---

## 4. `backend/api/ingest.py` the HTTP twin

```python
@router.post("/git", response_model=GitIngestResponse)
def ingest_git(payload: GitIngestRequest, db: Depends(get_db)):
    try:
        summary = ingest_git_repo(db, payload.repo_path, ...)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return GitIngestResponse(**summary)
```
A thin wrapper. All the work is in the service; the endpoint's only extra job is
turning a bad repo path (`ValueError`) into a clean **400** instead of a 500.
Registered in `backend/main.py` alongside the other routers.

New schemas in `backend/schemas.py`: `GitIngestRequest` (input),
`GitCommitIngested` (one row of the per-commit summary), and
`GitIngestResponse` (the whole result).

---

## 5. `demo/demo_phase8.py` proving it end-to-end

1. `POST /ingest/git` for **this repo** and print what was ingested per commit.
2. Ask a few "in the code history, what changed when…" questions via `/chat`.
3. For each answer, print the **commit hash(es)** listed in the sources.

The questions are phrased "in the code history…" so the router sends them to
**code memory**, where the full diffs live that's where the detail is.

---

## 6. What we saw when we ran it (live)

Ingesting this project's own 7 commits produced **14 code chunks** and **2
decision entries** (the Phase 5 and Phase 6 commit messages tripped the "why"
heuristic). Then, asking *"in the code history, what changed when adaptive
memory routing with LangGraph was added?"*:

- routed to **`['code', 'decision']`**,
- returned a detailed, accurate summary of the Phase 6 changes, and
- **cited commit `135e7679`** (both its code and decision entries) as the top
  sources.

Same for the multi-memory-split and embeddings questions each cited the right
commit (`24608e30`, `8b991fcf`).

### The one gotcha token budget

Git diff chunks are **large** (~800 tokens each), much bigger than the tiny
hand-written memories from Phase 5. With a small `CONTEXT_TOKEN_BUDGET` (we hit
this at budget `80`), a whole commit chunk can't fit the context slice, so it
gets **dropped** and the answer falls back to "I don't know."

That's not a Phase 8 bug it's the **Phase 7 token budget working correctly**.
The fix is simply to run with a healthy budget (`1500`–`2000`) so a full commit
fits. Lesson: **the size of your memories and the size of your budget have to
match.**

---

## 7. What to remember going forward

- **Real history is free training data.** Git already records what changed and
  often why ingesting it beats hand-writing memories.
- **The commit hash is the perfect `source_ref`** citations point at an exact,
  verifiable commit you can `git show`.
- **One source, two memories.** The same commit can be both a code fact (the
  diff) and a decision (the "why") routing later decides which one a question
  needs.
- **Reuse the write path.** New source, same `store_memory` no new storage
  code, so vectors and rows stay consistent with every other memory.
- **Big chunks need a big budget.** Match `CONTEXT_TOKEN_BUDGET` to the size of
  what you're storing, or the context builder will (correctly) drop it.
