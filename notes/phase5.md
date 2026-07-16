# 📘 Phase 5 — Multi-Memory Split

> A simple learning journal for Phase 5 of MemoryRAG. Written in plain,
> beginner-friendly language — meant to be pasted straight into Notion.

## TL;DR — what did we actually make?

We took the one big pile of embedded text and split it into **five separate
piles**, one per kind of knowledge:

| Memory type    | Lives in namespace     | Example |
|----------------|------------------------|---------|
| `document`     | `document_memory`      | a wiki page, a policy doc |
| `code`         | `code_memory`          | a function or class |
| `decision`     | `decision_memory`      | "we chose JWT because..." |
| `workflow`     | `workflow_memory`      | "deploy = test → build → ship" |
| `conversation` | `conversation_memory`  | "in the Q2 call we agreed to..." |

All five live inside the **same** Pinecone index (`memoryrag`), just in
separate **namespaces** (think: one filing cabinet, five drawers). We also
added two Postgres tables — `memory_types` (the five categories) and
`memories` (each saved entry) — to track what's stored where.

No auto-routing yet — you say which type to write/search. Picking the type
*automatically* is Phase 6. Phase 5 just builds the five clean shelves.

We proved the split is real (not fake) with `demo/demo_phase5.py`: it
searches every drawer with every type's question — 25 searches — and each
drawer only ever returns its own type, even when another type would be a
better match. That's true isolation, not just a label on each item.

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/embeddings/store.py` | Reworked to know about five namespaces + save/search memories in the right one |
| `backend/models/memory.py` | The `memory_types` + `memories` tables, the five type definitions, and the startup seeder |
| `backend/api/memories.py` | `POST /memories` (save one) and `POST /memories/search` (search one type) |
| `backend/schemas.py` | Now also describes the memory create/search request & response shapes |
| `demo/seed_phase5.py` | Fills each type with 2-3 example entries |
| `demo/demo_phase5.py` | Runs the 5×5 search matrix that proves the types are isolated |

For the deep, line-by-line version of every file above, see
[`phases/phase5.md`](../phases/phase5.md) — this note is the "story and
summary" version, that one is the "read every line" version.

---

## 🧠 New words explained super simply

- **Memory type** — a category of knowledge: document, code, decision,
  workflow, or conversation. The core idea of MemoryRAG is that different
  questions want different *types* of memory.
- **Namespace** — a labeled section *inside* one Pinecone index. Cabinet =
  index; drawer = namespace. A search opens exactly one drawer.
- **Index vs. namespace (and why it matters)** — an index is a whole cabinet
  and costs a slot on Pinecone's free plan; a namespace is a drawer inside it
  and is basically free. So we use ONE index with FIVE drawers instead of
  five cabinets — same isolation, no free-tier problems.
- **Reference data** — fixed, known rows the app always needs (here, the five
  memory types). We insert them automatically on startup.
- **Isolation vs. labeling** — labeling = "one pile, each item stamped with a
  type." Isolation = "five physically separate piles, so a search of one
  literally can't see the others." We built (and proved) isolation.
- **vector_id** — the id of an entry's embedding over in Pinecone, stored on
  its Postgres row. It's the link between "what/why" (Postgres) and "the
  searchable embedding" (Pinecone).

---

## 🛠️ The setup story — what we ran, and how it went

1. **Split one namespace into five.** The old single `documents` namespace
   became five: `document_memory`, `code_memory`, `decision_memory`,
   `workflow_memory`, `conversation_memory` — all inside the same index.

2. **Kept old document upload/chat working for free.** We added a `namespace`
   argument to the existing save/search functions with a sensible default
   (`document_memory`), so Phase 4's `/documents` and `/chat` moved over to
   the new document namespace *without any code change* on their side.

3. **Added two Postgres tables.** `memory_types` (the five categories, with the
   namespace each maps to) and `memories` (each saved entry, linked to its
   type and to its Pinecone `vector_id`). The five type rows get seeded
   automatically on startup, so they're always there.

4. **Built `POST /memories`** — give it `{memory_type, content, source_ref}`;
   it saves a row, embeds the content into that type's namespace, and links
   the two together. And **`POST /memories/search`** — give it a type + query,
   and it searches only that type's drawer.

5. **A small Pinecone gotcha:** Pinecone metadata can't hold `null`. So when a
   memory has no `source_ref`, we *leave the key out* entirely rather than set
   it to `None` — otherwise the save would error.

6. **Proved isolation live.** Ran `demo_phase5.py`: it seeds entries, then does
   a 5×5 matrix of searches (every drawer × every type's question). All 25
   came back OK — each drawer returned only its own type. The "spotlight"
   check fired a clear *workflow* question ("steps to ship to production") at
   all five drawers; only `workflow_memory` returned the deploy runbook, and
   the other four returned their own unrelated entries — because the runbook
   physically isn't in those drawers. Isolation, demonstrated, not assumed.

7. **Confirmed the relational side too.** Checked Postgres: all five
   `memory_types` present, every `memories` row linked to its type, and every
   row had a `vector_id` — so the "track what's stored where" goal is real.

---

## 🧪 How to try it yourself

### Terminal 1 — start the server

```bash
./run.sh            # the five memory_types auto-seed on startup
```

### Terminal 2 — seed and prove isolation

```bash
conda activate memoryrag
python3 demo/seed_phase5.py http://localhost:8010    # optional: nice example entries
python3 demo/demo_phase5.py http://localhost:8010    # seeds its own + runs the 5x5 proof
```

Watch the matrix print `[OK]` for all 25 searches, ending in "the five memory
types are truly isolated."

### Or, by hand in Swagger UI (`http://localhost:8010/docs`)

1. **`POST /memories`** → send e.g. `{"memory_type": "decision", "content":
   "Decision: use X because Y", "source_ref": "adr/1"}`. Try a couple
   different `memory_type` values.
2. Wait ~10-15 seconds (Pinecone settling, same as earlier phases).
3. **`POST /memories/search`** → `{"memory_type": "decision", "query": "why
   did we pick X"}` → you get back only decision entries.
4. The revealing test: search `{"memory_type": "code", "query": "why did we
   pick X"}` (a decision-flavored question aimed at the *code* drawer) — you
   will NOT get the decision back, because it lives in a different namespace.
   That's isolation.

---

## ✅ What to remember going forward

- **Namespaces = free isolation inside one index.** Five drawers in one
  cabinet keeps us on the free tier while fully separating each type.
- **Prove isolation, don't assume it.** A search scoped to one namespace
  can't see the others; the 5×5 matrix shows that, instead of trusting a tag.
- **Postgres and Pinecone do different jobs, linked by `vector_id`.** Postgres
  = what/why/relationships; Pinecone = the searchable embedding.
- **Seed reference data idempotently on startup** — always present, never
  duplicated, safe on every restart.
- **Use a foreign key when the parent always exists** (memory → memory_type),
  and skip it when it might not (Phase 4's message → project). Phase 4 and 5
  show both sides of that call.
- **This phase stops before routing on purpose.** We built and isolated the
  five memories; letting the system *choose* between them automatically is
  Phase 6.
