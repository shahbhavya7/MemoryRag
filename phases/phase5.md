# Phase 5 Multi-Memory Split (Beginner Notes)

## What are we even building in this phase?

Up to now, every embedded piece of text went into ONE big pile (a single
Pinecone namespace called `documents`). That works, but it throws away
something valuable: *what kind* of knowledge each piece is. A code snippet, a
past decision, a deploy runbook, and a meeting summary are all very different
things, and questions about them are best answered by looking in the right
place.

Phase 5 splits that one pile into **five separate piles**, one per *memory
type*:

| Memory type    | Pinecone namespace     | What goes in it |
|----------------|------------------------|-----------------|
| `document`     | `document_memory`      | PDFs, docs, notes, wiki pages |
| `code`         | `code_memory`          | functions, classes, APIs, READMEs |
| `decision`     | `decision_memory`      | structured engineering decisions |
| `workflow`     | `workflow_memory`      | processes / step-by-step flows |
| `conversation` | `conversation_memory`  | important discussions worth keeping |

Crucially, this is still **one Pinecone index** (`memoryrag`) the five piles
are separate **namespaces** *inside* it, not five separate indexes. (More on
why that matters below.)

This phase does NOT yet decide *which* memory to use for a given question —
you always say the type explicitly when writing or searching. That automatic
decision ("this question smells like a workflow question, look in
workflow_memory") is **Adaptive Memory Routing**, and it's Phase 6. Phase 5
just builds the five clean, isolated shelves that routing will later choose
between.

We proved the split is real with `demo/demo_phase5.py`, which searches every
namespace with every type's query (a 5×5 matrix) and confirms each namespace
only ever returns its own type even when the query would match another
type's content better. That's *isolation*, not just *labeling*.

---

## 1. New words used in this phase

- **Memory type** a category of knowledge (document / code / decision /
  workflow / conversation). The whole idea of MemoryRAG is that different
  questions are best answered from different *types* of memory.
- **Namespace (Pinecone)** a labeled partition *inside* a single index. Think
  of the index as a filing cabinet and each namespace as one drawer. Vectors
  in one drawer are completely separate from vectors in another a search
  targets exactly one drawer.
- **Index vs. namespace** an *index* is the whole cabinet (and costs a slot
  on Pinecone's free tier); a *namespace* is a drawer inside it (effectively
  free, unlimited). We use one index with five namespaces rather than five
  indexes, specifically to stay within the free tier.
- **Reference data / seed data** rows that describe fixed, known categories
  (here, the five `memory_types`). We insert them automatically on startup so
  the app always has them, rather than making a user create them by hand.
- **Isolation vs. labeling** *labeling* would be "everything's in one pile
  but each item has a `type` tag." *Isolation* is stronger: each type lives in
  a physically separate namespace, so a search of one type literally cannot
  see another's data. This phase achieves (and proves) isolation.

---

## 2. The folder structure now

```
MemoryRag/
├── backend/
│   ├── main.py                    # now seeds the 5 memory types + mounts /memories
│   ├── schemas.py                 # now has memory create/search shapes
│   ├── api/
│   │   └── memories.py            # NEW POST /memories and POST /memories/search
│   ├── models/
│   │   └── memory.py              # NEW MemoryType + Memory tables + the 5 type defs + seeder
│   └── embeddings/
│       └── store.py                # reworked five namespaces + memory upsert/search helpers
├── demo/
│   ├── seed_phase5.py              # NEW seeds 2-3 example entries per memory type
│   └── demo_phase5.py              # NEW proves the five namespaces are isolated
└── (no new dependencies this phase)
```

Notice there are **no new packages** this phase it's a pure architecture
change built entirely on the Pinecone + Postgres pieces we already had.

---

## 3. Going file by file

### `backend/embeddings/store.py` "one index, five namespaces"

The key new piece is the namespace map:

```python
MEMORY_NAMESPACES = {
    "document": "document_memory",
    "code": "code_memory",
    "decision": "decision_memory",
    "workflow": "workflow_memory",
    "conversation": "conversation_memory",
}
DOCUMENT_NAMESPACE = MEMORY_NAMESPACES["document"]
```

- This dict is the one place that maps a short **type name** (what the API
  uses) to its **namespace** (what Pinecone uses). Everything else refers back
  to it, so there's a single source of truth.
- **`DOCUMENT_NAMESPACE`** the old Phase 3/4 document uploads now live in
  `document_memory`. The existing `add_chunks()` and `search()` functions
  gained a `namespace` parameter that *defaults* to `DOCUMENT_NAMESPACE`:

```python
def add_chunks(chunks, embeddings, project_id, source_filename, namespace=DOCUMENT_NAMESPACE): ...
def search(query_embedding, top_k, namespace=DOCUMENT_NAMESPACE, project_id=None): ...
```

Because the new parameter has a default, the Phase 4 callers (`/documents/upload`
and `/chat`) didn't need any code change they automatically moved from the
old `documents` namespace to `document_memory`. Adding an optional parameter
with a safe default is a clean way to extend behavior without breaking
existing callers.

Then two new helpers, specifically for memories (which store *content* and
type info in metadata, unlike document chunks):

```python
def add_memory_vector(namespace, embedding, memory_id, memory_type, content, source_ref) -> str:
    metadata = {"memory_id": memory_id, "memory_type": memory_type, "content": content}
    if source_ref is not None:
        metadata["source_ref"] = source_ref
    vector_id = str(uuid.uuid4())
    _get_index().upsert(vectors=[{"id": vector_id, "values": embedding, "metadata": metadata}],
                        namespace=namespace)
    return vector_id
```

- **`if source_ref is not None:`** this guard matters: Pinecone metadata
  **cannot contain null values**. If `source_ref` is missing, we must *omit*
  the key entirely rather than set it to `None`, or the upsert would error.
  A small but real gotcha of storing metadata in Pinecone.
- **returns `vector_id`** the caller (the endpoint) saves this back onto the
  Postgres row, creating the link between "the row" and "its embedding."

```python
def search_memories(namespace, query_embedding, top_k) -> list[dict]:
    result = _get_index().query(vector=query_embedding, top_k=top_k,
                                namespace=namespace, include_metadata=True)
    return [{"memory_id": m["metadata"].get("memory_id"),
             "memory_type": m["metadata"]["memory_type"],
             "content": m["metadata"]["content"],
             "source_ref": m["metadata"].get("source_ref"),
             "score": m["score"]} for m in result["matches"]]
```

- The `namespace` argument is the whole point: a search is *scoped to one
  namespace*. There is no way for this query to see vectors in a different
  namespace that's what makes the isolation structural, enforced by
  Pinecone itself, not by us filtering afterward.

### `backend/models/memory.py` "the two new tables + the five type defs"

```python
MEMORY_TYPE_DEFS = [
    {"name": "document", "namespace": "document_memory", "description": "..."},
    {"name": "code", "namespace": "code_memory", "description": "..."},
    ... (decision, workflow, conversation) ...
]

class MemoryType(Base):
    __tablename__ = "memory_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    namespace = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, index=True)
    memory_type_id = Column(Integer, ForeignKey("memory_types.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_ref = Column(String, nullable=True)
    vector_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- **`memory_types`** is *reference data* five fixed rows describing the five
  categories. Storing `namespace` right in the row makes the "which type lives
  where" mapping explicit and queryable in the database, which directly
  supports the phase's goal of *tracking what's stored where relationally*.
- **`memories`** is the actual log of stored entries. Two links make it the
  connective tissue of the whole system:
  - **`memory_type_id` (a real `ForeignKey`)** ties each entry to exactly one
    of the five types. Unlike the `messages` table in Phase 4 (which
    deliberately has no FK), here a foreign key is correct: the five types are
    fixed, always-present reference rows, so a memory *must* belong to a real
    one.
  - **`vector_id`** the id of this entry's vector over in Pinecone. This is
    the bridge between the relational world (Postgres: "what and why") and the
    vector world (Pinecone: "the embedding used for search"). Given a row you
    can find its vector; the type tells you which namespace to look in.

```python
def seed_memory_types(db):
    existing = {mt.name for mt in db.query(MemoryType).all()}
    for definition in MEMORY_TYPE_DEFS:
        if definition["name"] not in existing:
            db.add(MemoryType(**definition))
    db.commit()
```

- **Idempotent seeding** it only inserts types that aren't already there, so
  running it on *every* startup is safe. This is the standard way to guarantee
  reference data exists without creating duplicates or erroring on restart.

### `backend/api/memories.py` "write a memory, search a memory type"

```python
@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(payload, db):
    memory_type = _get_memory_type_or_400(db, payload.memory_type)   # validate the type name
    memory = Memory(memory_type_id=memory_type.id, content=payload.content, source_ref=payload.source_ref)
    db.add(memory); db.commit(); db.refresh(memory)                  # 1. save row -> get its id
    embedding = embed_query(payload.content)
    vector_id = add_memory_vector(memory_type.namespace, embedding, memory.id,
                                  memory_type.name, payload.content, payload.source_ref)  # 2. embed into the right namespace
    memory.vector_id = vector_id; db.commit(); db.refresh(memory)    # 3. link row -> vector
    return MemoryOut(...)
```

The three numbered steps are the whole write path, and the *order* is
deliberate:
1. **Save the Postgres row first**, so we have a real `memory.id` to stamp onto
   the vector's metadata (letting a search result point back to its row).
2. **Embed and upsert into that type's namespace** `memory_type.namespace`
   comes straight from the reference table, so the content can only ever land
   in the correct pile.
3. **Write the returned `vector_id` back onto the row**, completing the
   two-way link between Postgres and Pinecone.

- **`_get_memory_type_or_400`** validates the requested type against the
  reference table and returns a clear `400` listing the valid types if it's
  wrong, instead of silently mis-filing content. Same "fail early and clearly"
  habit as earlier phases' `_get_..._or_404` helpers.

```python
@router.post("/search", response_model=MemorySearchResponse)
def search_memory(payload, db):
    memory_type = _get_memory_type_or_400(db, payload.memory_type)
    query_embedding = embed_query(payload.query)
    results = search_memories(memory_type.namespace, query_embedding, payload.top_k)
    return MemorySearchResponse(results=[MemorySearchResult(**r) for r in results])
```

- This is the **direct, un-routed** search the phase is about: the caller names
  the type, we look up its namespace, and search *only* there. Phase 6 will add
  a layer *above* this that picks the type automatically but the isolated
  per-type search built here is what routing will ultimately call.

### `backend/main.py` "seed the types on startup"

```python
_db = SessionLocal()
try:
    seed_memory_types(_db)
finally:
    _db.close()
```

Runs once at startup (right after `create_all()` builds the tables), guaranteeing
the five reference rows exist before any request arrives. The `try/finally`
makes sure the temporary session is always closed, even if seeding raised —
the same session-hygiene discipline as Phase 1's `get_db()`.

---

## 4. Proving isolation, not just labeling

The weak version of a test would be: "search decision memory, get decisions
back." But that could pass even in a single-pile-with-tags design. So
`demo/demo_phase5.py` does the strong version a **5×5 matrix**:

- For every namespace `N` (all five), and every type's probe query `P` (all
  five), search `N` using `P`'s query and record which types come back.
- The assertion: **searching namespace `N` must return only `N`'s entries no
  matter which type's query we used.**

That's 25 searches. Several of them deliberately use a query that semantically
*belongs* to a different type (e.g. searching `decision_memory` with a
workflow-flavored query). If the design were "one pile with tags + a filter,"
a bug in the filter could leak the wrong type. But with true namespace
isolation, the other type's content simply *isn't in that namespace*, so it
can never surface which is exactly what the run confirmed (all 25 = OK).

The "spotlight" section drives it home: it fires the same "steps to ship the
backend to production" (a clear workflow question) at all five namespaces. Only
`workflow_memory` returns the deploy runbook; each other namespace returns its
own best (unrelated) entry, because the runbook physically isn't in those
namespaces. That's the difference between isolation and labeling made visible.

---

## 5. How the old document flow fits in

`/documents/upload` and `/chat` from Phases 3–4 still work unchanged, but their
data now lives in the `document_memory` namespace (renamed from the old
`documents`). They don't create `memories` rows they remain the
chunk-oriented document path. The new `/memories` endpoint is the
relationally-tracked, type-aware path. They coexist: think of `/documents` as
"bulk-upload a file as document memory" and `/memories` as "record one typed
memory entry with full relational tracking." A later phase could unify them,
but keeping them separate here avoided disturbing the working Phase 4 chat.

---

## 6. The big ideas to remember from this phase

- **Namespaces give free isolation inside one index.** Five drawers in one
  cabinet, not five cabinets which keeps us on Pinecone's free tier while
  still keeping each memory type's vectors completely separate.
- **Isolation is stronger than labeling, and it's worth *proving*.** A search
  scoped to a namespace physically cannot see other namespaces; the 5×5 matrix
  demonstrates that, rather than trusting a `type` tag.
- **Postgres and Pinecone play different roles, linked by `vector_id`.**
  Postgres tracks *what* a memory is and *why* (type, content, source,
  timestamps, relationships); Pinecone stores the *embedding* for search. The
  `vector_id` column is the bridge.
- **Reference data should be seeded idempotently on startup** always present,
  never duplicated, safe across restarts.
- **A foreign key is right when the referenced rows are fixed and always
  present** (memory → memory_type), and wrong when the "parent" may not exist
  (Phase 4's message → project) the two phases show both sides of that
  judgment call.
- **This phase deliberately stops short of routing.** It builds and isolates
  the five memories; *choosing* between them automatically is the next phase.
