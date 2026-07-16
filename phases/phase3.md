# Phase 3 — Embeddings + Vector Search with Pinecone (Beginner Notes)

## What are we even building in this phase?

Phases 1 and 2 gave us a backend that saves and protects structured rows —
Projects, Chats, Users. All of those are things with an exact shape you can
look up by an exact `id`.

Phase 3 adds a completely different kind of lookup: **search by meaning**,
not by exact match. You give the app a chunk of free-form text (a paragraph,
a document, a note), and later you can ask a question in your own words —
not the original wording — and get back the most relevant chunk anyway.

This is the foundation of RAG (Retrieval-Augmented Generation) — the whole
reason MemoryRAG exists. Before an LLM can answer "why did we migrate to
Postgres?", something first has to find the *right* stored text to hand the
LLM as context. Phase 3 builds that "find the right stored text" piece,
without any LLM involved yet — just embeddings and a vector database.

This phase uses **Pinecone**, a *hosted* vector database — unlike Postgres
in Phase 1, there's nothing to install locally at all. You sign up for a
free account, get an API key, and the app talks to Pinecone's servers over
the internet instead of reading/writing local files.

We proved the logic with `demo/demo_phase3.py`, which uploads a paragraph
about a made-up topic (so we can be certain any correct answer comes from
*our* document, not something the model already "knew"), plus a second,
unrelated made-up document as a decoy — then asks a question that **fully
paraphrases** the source text with no shared words at all, and confirms the
real document still wins over the decoy every time.

> **Note on live verification:** this phase requires a real Pinecone API key
> to run — it's a hosted third-party service, so there's no way to spin one
> up locally the way we did with Postgres. Once a real key was available,
> everything below was verified end-to-end against a real Pinecone account:
> the index was created live, real vectors were upserted and queried, and
> the demo script passed. That run also surfaced a real, worth-knowing
> Pinecone quirk — see section 4a below.

---

## 1. New words used in this phase

- **Embedding** — a way of turning a piece of text into a long list of
  numbers (a **vector**) that captures its *meaning*. Two pieces of text
  that mean similar things end up with similar-looking number lists, even
  if they don't share a single word.
- **Vector database** — a database specialized in storing these number
  lists and quickly answering "which stored vectors are closest in meaning
  to this new vector?" We use **Pinecone** for this.
- **Hosted / serverless** — instead of installing and running the database
  yourself (like we did with Postgres in Phase 1), Pinecone runs entirely
  on Pinecone's own servers. Your app just talks to it over the internet
  using an API key — there's no local process, no local data folder, and
  nothing to start or stop on your machine.
- **Index** — Pinecone's version of a "database" — the top-level container
  that holds your vectors. Every index has a fixed **dimension** (how many
  numbers are in each vector) and a fixed **metric** (how "closeness" is
  measured) that can't be changed after creation.
- **Namespace** — a way of keeping separate groups of vectors *inside the
  same index*, without needing a whole separate index per group. Think of
  an index as a filing cabinet and a namespace as one labeled drawer in it
  — you can have many drawers in one cabinet.
- **Upsert** — "update or insert": save a vector under a given id, whether
  or not that id already existed. If it existed, its old value is replaced;
  if not, it's created fresh. This is Pinecone's term for "save this."
- **Chunking** — splitting a long document into smaller pieces before
  embedding it. Embedding models work best on a paragraph or two at a time,
  not an entire book at once, and smaller chunks mean more precise search
  results later (you get back the *specific* relevant paragraph, not an
  entire document).
- **Chunk overlap** — letting neighboring chunks share a little bit of text
  at their boundary, so an idea that happens to span the exact cut point
  between two chunks doesn't get awkwardly sliced in half with no chunk
  containing the whole thought.
- **Cosine similarity score** — a number describing how close two vectors
  are in meaning. With Pinecone's `cosine` metric, a **higher** score means
  **more** similar (this is the opposite convention from a "distance,"
  where lower would mean closer — worth remembering if you've read about
  other vector databases that use distance instead).
- **Semantic search** — searching by *meaning* (using embeddings) instead of
  by matching exact words. This is the entire point of this phase, and the
  demo script goes out of its way to prove it's real, not an illusion of
  shared keywords.

---

## 2. The folder structure now

```
MemoryRag/
├── backend/
│   ├── main.py                    # now also wires up /documents + ensures the Pinecone index exists
│   ├── schemas.py                 # now also has upload/search shapes
│   ├── api/
│   │   └── documents.py           # NEW — /documents/upload, /documents/search
│   └── embeddings/
│       ├── chunking.py            # NEW — splits long text into overlapping pieces
│       ├── model.py               # NEW — loads BAAI/bge-small-en-v1.5, turns text into vectors
│       └── store.py                # NEW — talks to the hosted Pinecone index
├── demo/
│   └── demo_phase3.py              # NEW — proves semantic search actually works
└── requirements.txt                 # a few new packages
```

Notice there's no local `chroma_data/`-style folder in this phase — because
Pinecone is hosted, all the actual vector data lives on Pinecone's servers,
not on your disk. The only thing your machine needs is the `PINECONE_API_KEY`
to authenticate.

Same idea as before: each new file has exactly one job. `chunking.py` only
knows how to split text. `model.py` only knows how to turn text into
numbers. `store.py` only knows how to talk to Pinecone. `documents.py` is the
thin layer on top that wires those three together into actual web
addresses.

---

## 3. Going file by file

### `backend/embeddings/chunking.py` — "splitting long text into pieces"

```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks
```

- **Why count words instead of "real" tokens?** An embedding model actually
  thinks in *tokens* (roughly, word-pieces — not quite whole words, not
  quite individual letters). Counting exact tokens would need pulling in
  the specific tokenizer library that model uses. Since the *goal* here is
  just "keep each chunk a reasonable, roughly-500-ish-token size," counting
  words is a close enough approximation that keeps this file dependency-free
  and easy to understand — a deliberate simplification for a learning
  project, not a production-grade token counter.
- **The sliding window**: `start = end - overlap` is the key trick. Instead
  of the next chunk starting exactly where the last one ended, it starts
  `overlap` words *earlier*, so the last 50 words of one chunk are also the
  first 50 words of the next chunk. This means an idea that happens to
  straddle a cut point still appears *whole* in at least one of the two
  chunks.
- **`if end >= len(words): break`** — without this, once we reached the very
  last chunk, the "go back `overlap` words" logic would create an endless
  loop of tiny overlapping chunks at the tail end. This stops cleanly the
  moment we've covered every word at least once.

### `backend/embeddings/model.py` — "turning text into vectors"

```python
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    return _get_model().encode(texts, normalize_embeddings=True).tolist()

def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
```

- **`_model: SentenceTransformer | None = None`, then `_get_model()`** — this
  is a manual **lazy singleton**: the actual model (a real neural network,
  ~130MB of weights) only gets loaded into memory the *first* time it's
  actually needed, not the moment the app starts up. After that first call,
  it's kept in the `_model` variable and reused for every future request —
  loading a model like this is slow (seconds), so we absolutely don't want
  to redo it on every single request.
- **`global _model`** — normally, a Python function can't change a variable
  defined outside it; `global` explicitly says "no, really, update the
  actual outer `_model` variable, don't just create a local copy of the
  name."
- **`SentenceTransformer("BAAI/bge-small-en-v1.5")`** — this line is what
  actually downloads the model from Hugging Face the very first time it
  runs (and caches it under `~/.cache/huggingface` afterward, so it's only
  ever downloaded once per machine, not once per app restart). This part is
  unrelated to Pinecone — it's a separate, local, one-time download from a
  different service (Hugging Face) purely for running the embedding model.
- **`.encode(texts, normalize_embeddings=True)`** — runs the model, turning
  a list of text strings into a list of number-vectors, each with exactly
  384 numbers (this model's fixed output size). `normalize_embeddings=True`
  rescales every vector to the same overall length, so that comparing two
  vectors' *similarity* isn't accidentally skewed by one just having bigger
  numbers than the other (only the *direction* of the vector should matter,
  not its raw size) — this matters even more with Pinecone's `cosine`
  metric, which is specifically a direction-based comparison.
- **`embed_query`** — a small convenience wrapper: searching only ever
  embeds one piece of text at a time (the question), so this just calls the
  same underlying function with a one-item list and unwraps the single
  result, so callers don't have to deal with list-of-one plumbing themselves.

### `backend/embeddings/store.py` — "talking to Pinecone"

```python
import os
import time
import uuid

from pinecone import Pinecone, ServerlessSpec

INDEX_NAME = "memoryrag"
DIMENSION = 384  # must match BAAI/bge-small-en-v1.5's output size
NAMESPACE = "documents"

_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
```

- **`Pinecone(api_key=os.getenv("PINECONE_API_KEY"))`** — same pattern as
  `DATABASE_URL` and `SECRET_KEY` in earlier phases: the secret comes from
  an environment variable, never hardcoded. Unlike those earlier values
  though, there's no sensible *fallback default* here — Pinecone is a real
  third-party account, so if this variable is missing, the app fails
  immediately and loudly at startup, which is exactly what we want (a
  confusing failure deep inside a request later would be much worse than
  an obvious one immediately).
- **`DIMENSION = 384`** — every vector saved into this index must have
  *exactly* this many numbers, forever, because that's fixed when the index
  is created. `BAAI/bge-small-en-v1.5` always outputs 384 numbers per
  embedding, so this constant just has to match that model's fixed output
  size.

```python
def ensure_index_exists() -> None:
    existing_names = [index["name"] for index in _pc.list_indexes()]
    if INDEX_NAME in existing_names:
        return

    _pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    while not _pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(1)
```

This is the "guard so it doesn't error on subsequent runs" logic from the
brief, and it's called once from `main.py` at startup (see below):

- **`_pc.list_indexes()`** — asks Pinecone "what indexes already exist in my
  account?" and we check if `"memoryrag"` is already one of them.
- **`if INDEX_NAME in existing_names: return`** — if it already exists, we
  do nothing and return immediately. This is the actual guard: without it,
  every single app restart would try to *create* the index again, and
  Pinecone would reject that with an error, since an index with that name
  already exists. Checking first means restarting the app is always safe.
- **`ServerlessSpec(cloud="aws", region="us-east-1")`** — tells Pinecone
  *where* to physically host this index. `us-east-1` is specifically called
  out here because Pinecone's free "Starter" plan only allows serverless
  indexes in this exact region — using a different region would fail on a
  free account.
- **`while not _pc.describe_index(INDEX_NAME).status["ready"]: time.sleep(1)`**
  — creating a brand-new index isn't instant on Pinecone's side; it takes a
  few seconds to actually become usable. This loop just waits, checking
  roughly once a second, until Pinecone confirms it's ready, so that the
  very next line of code that tries to actually use the index doesn't fail
  by running too soon.

```python
def _get_index():
    return _pc.Index(INDEX_NAME)
```

A small helper that gets a handle to the actual index object, used by both
functions below — keeping this in one place means if how we look up the
index ever needs to change, there's only one line to update.

```python
def add_chunks(chunks: list[str], embeddings: list[list[float]], project_id: int, source_filename: str) -> int:
    vectors = [
        {
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {"project_id": project_id, "source_filename": source_filename, "chunk_text": chunk},
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    _get_index().upsert(vectors=vectors, namespace=NAMESPACE)
    return len(vectors)
```

- **`"id": str(uuid.uuid4())`** — same idea as Phase 1's auto-incrementing
  Postgres `id` — every vector needs a unique identifier. Pinecone doesn't
  generate these for you the way Postgres does, so we generate a random,
  practically-guaranteed-unique id ourselves.
- **`"values": embedding`** — the actual vector (list of 384 numbers) that
  Pinecone will use for similarity comparisons.
- **`"metadata": {...}`** — extra information stored *alongside* the vector,
  not used in the similarity math itself but returned back to us in search
  results. Notice `chunk_text` is stored *inside* metadata here — unlike
  Chroma (which has a dedicated separate "document text" field), Pinecone
  only really has "a vector + its metadata," so we simply put the actual
  chunk's text into the metadata dictionary ourselves, under our own chosen
  key name, exactly as the brief specifies.
- **`_get_index().upsert(vectors=vectors, namespace=NAMESPACE)`** — sends
  all the chunks for this one upload in a single batched request. `namespace=NAMESPACE`
  (`"documents"`) tells Pinecone which "drawer" of the index to save these
  into — later phases will use different namespace names for different
  memory types, all within this same one index.

```python
def search(query_embedding: list[float], top_k: int) -> list[dict]:
    result = _get_index().query(
        vector=query_embedding,
        top_k=top_k,
        namespace=NAMESPACE,
        include_metadata=True,
    )
    return [
        {
            "text": match["metadata"]["chunk_text"],
            "score": match["score"],
            "metadata": {
                "project_id": match["metadata"]["project_id"],
                "source_filename": match["metadata"]["source_filename"],
            },
        }
        for match in result["matches"]
    ]
```

- **`.query(vector=query_embedding, top_k=top_k, namespace=NAMESPACE, include_metadata=True)`**
  — the actual "find similar things" call: compare this one query vector
  against everything stored in the `"documents"` namespace, and return the
  `top_k` closest matches. `include_metadata=True` is required, or Pinecone
  would only hand back ids and scores, without the actual chunk text or our
  other metadata fields.
- **`match["score"]`** — this is Pinecone's cosine similarity for this
  match: **higher is better**, unlike some other vector databases (including
  Chroma, used in an earlier version of this phase) which report a
  *distance* instead, where lower is better. Worth double-checking this
  convention any time you work with a new vector database — it's an easy
  detail to get backwards.
- **Reshaping the result** — Pinecone gives back a list of "matches," each
  with its own `metadata` dictionary. This list comprehension just pulls the
  fields we care about into a clean, flat dictionary per match (`text`,
  `score`, `metadata`) — the exact same output shape our API layer expects,
  regardless of which vector database happens to be underneath. That
  consistency is exactly why `add_chunks`/`search` were kept as the only two
  functions this module exposes — `backend/api/documents.py` never needed
  to change at all when we swapped from Chroma to Pinecone, because it only
  ever talks to these two functions, never to Pinecone or Chroma directly.

### `backend/main.py` — wiring the index check into startup

```python
from backend.embeddings.store import ensure_index_exists

Base.metadata.create_all(bind=engine)
ensure_index_exists()
```

Same idea as Phase 1's `Base.metadata.create_all(bind=engine)` — a
"make sure the thing we need exists" call that runs once, the moment the
app starts, right alongside the Postgres table setup. This is where "on
startup, check if [the index] exists and create it if not" from the brief
actually happens.

### `backend/api/documents.py` — unchanged from the Chroma version

This file didn't need a single line changed when we swapped vector
databases — it only ever imports `add_chunks` and `search` from
`backend/embeddings/store.py`, never anything Pinecone- or Chroma-specific
directly. This is the benefit of keeping a thin, clearly-scoped module
boundary: the *whole* vector database could be swapped out by rewriting
one file.

### `backend/schemas.py` — unchanged from the Chroma version

```python
class DocumentUploadOut(BaseModel):
    source_filename: str
    chunks_created: int

class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5

class DocumentSearchResult(BaseModel):
    text: str
    score: float
    metadata: dict

class DocumentSearchResponse(BaseModel):
    results: list[DocumentSearchResult]
```

Same "separate shape for what goes in vs. what comes out" pattern as every
earlier phase. These shapes didn't need to change either — `score: float`
still means "a number describing similarity," it just now comes from
Pinecone's cosine similarity instead of Chroma's distance.

---

## 4. Making the demo actually *prove* semantic search (not just claim it)

Uploading only *one* document would make every search trivially "find" it
— there'd be nothing else in the store to *not* find, so that wouldn't
actually prove anything.

The fix: `demo/demo_phase3.py` uploads a **second, unrelated, made-up
document** (a fictional kite tournament) as a decoy, tagged with a different
`project_id`. Now every search has to actually **choose** between two real
candidates. The demo asserts, for every query, that the Glimmerwood-squirrel
chunk (`project_id == 1`) ranks first — including for the query "How do
these squirrels build their homes without using twigs?", which shares
**zero** words with the source text's actual phrase ("driftnests... out of
moss and spider silk"). A plain keyword search would have no reason to
connect "build their homes" with "driftnests... moss and spider silk" — but
the embedding model correctly recognizes they mean the same thing.

This is also why both documents are about deliberately **made-up, fictional
topics** — if we'd used a real, well-known subject, we couldn't be sure
whether a correct answer came from *our* uploaded text or from things the
embedding model already learned about that real topic during its own
training. Made-up topics rule that out entirely.

This assertion logic didn't need to change at all when we switched from
Chroma to Pinecone — `result["matches"][0]` (or `result.json()["results"][0]`
from the API's point of view) is meant to always be the single best match,
regardless of whether "best" was decided by a distance (lower wins) or a
similarity score (higher wins) — both databases sort their own results,
best match first. In practice, running this live against a real Pinecone
account surfaced an exception to that, covered next.

---

## 4a. A real bug we hit during live verification: Pinecone's eventual consistency

Once a real `PINECONE_API_KEY` was available, this phase was tested
end-to-end for real — including the very first live index creation, real
upserts, and real queries. The demo initially **failed intermittently**: the
very first search immediately after the two uploads occasionally ranked the
unrelated kite-tournament chunk *above* the correct squirrel chunk, even
though the squirrel chunk's score was clearly higher (e.g. `0.81` vs.
`0.47` — not a close call at all).

This was tracked down by bypassing the API entirely and calling Pinecone's
own client directly, right after upserting, which reproduced the same
mis-ordering — proving it wasn't a bug in `search()`'s reshaping logic (it
does no sorting of its own; it just preserves whatever order Pinecone
returns). Re-running the *exact same query* roughly a minute later returned
the correct order every time.

This is **Pinecone serverless's eventual consistency**: immediately after
the very first upserts into a brand-new namespace, the index can take a
short but sometimes-surprisingly-long while (observed up to about a minute
in testing) to fully "settle" before similarity search reliably reflects
what was just written — not merely omitting the newest vectors, but
occasionally ranking them incorrectly relative to older ones in the same
tiny window. A short fixed `time.sleep(5)` was not reliable enough to avoid
this.

**The fix**, in `demo/demo_phase3.py`'s `wait_for_index_to_settle()`: instead
of guessing a sleep duration, poll a known "canary" query every few seconds
(up to a 60-second cap) until its expected top result actually shows up
correctly ranked, then proceed with the real demonstration queries. This
is a general pattern worth remembering for *any* eventually-consistent
system (not just Pinecone) — poll for the actual condition you need to be
true, rather than sleeping for a guessed amount of time and hoping it was
long enough.

**Lesson:** a real third-party hosted service can behave differently than
its docs' happy-path examples suggest, especially right at the boundary of
"data was just written." Reasoning about code correctness in the abstract
caught everything else in this phase, but this particular timing quirk
only surfaced by actually running it live against the real service —
another reminder of why "prove it works, don't just hand over the code" is
worth the extra effort.

---

## 5. New packages, and why they're each needed

```
python-multipart==0.0.17
pinecone==9.1.0
sentence-transformers==3.3.1
```

- **`python-multipart`** — FastAPI needs this installed to parse multipart
  form data (`Form`, `File`, `UploadFile`) at all; without it, the app would
  fail at startup with an error pointing you straight at this missing
  dependency.
- **`pinecone`** — the official Pinecone Python client, used to create the
  index, and to upsert/query vectors over the network.
- **`sentence-transformers`** — the library that actually runs the
  `BAAI/bge-small-en-v1.5` embedding model. It pulls in `torch` (a large
  machine learning library) as a dependency, which is why installing this
  phase's requirements takes noticeably longer and downloads noticeably
  more than earlier phases.

---

## 6. Environment variables — one new one, `PINECONE_API_KEY`

```
PINECONE_API_KEY=your-pinecone-api-key-here
```

Same rule as every other secret in this project: never hardcode it, never
commit a real one to git. Unlike `DATABASE_URL`, there's no reasonable local
fallback default — Pinecone is a hosted third-party service, so this value
*must* come from a real account. `.env.example` includes a comment pointing
at [pinecone.io](https://www.pinecone.io) for signing up for a free key.

---

## 7. The big ideas to remember from this phase

- **Embeddings turn meaning into numbers** — that's the entire trick behind
  semantic search, and it's what makes "search by paraphrase" possible at
  all, unlike a plain keyword search.
- **Chunk before you embed.** Smaller, overlapping pieces of text give you
  more precise search results later, and overlap protects against an idea
  getting awkwardly split exactly at a chunk boundary.
- **A lazy singleton avoids reloading an expensive resource** (here, a
  ~130MB neural network) **on every request** — load it once, keep it
  around, reuse it.
- **You must embed queries with the exact same model you used for storing**
  — comparing vectors from two different embedding models is meaningless,
  like comparing distances measured in miles against distances measured in
  kilometers without converting first.
- **A hosted vector database (Pinecone) needs no local process to run, but
  does need a guarded "create if missing" startup check** — since you can't
  assume the index already exists the very first time the app ever runs
  against a fresh account.
- **Similarity score direction varies by database/metric — always check
  which way is "better."** Pinecone's cosine metric here is higher-is-better;
  other setups (like a plain distance) can be the opposite.
- **A single-item test proves nothing about search quality.** Always test
  retrieval against at least one deliberately unrelated "decoy" item, so a
  correct result actually demonstrates the ranking works, not just that the
  only available answer got returned.
- **Keeping API code decoupled from a specific vector database pays off
  immediately** — swapping Chroma for Pinecone required rewriting exactly
  one file (`store.py`); `documents.py`, `schemas.py`, and the demo's core
  logic needed no changes at all.
- **A hosted, eventually-consistent database can briefly return stale or
  mis-ordered results right after a write** — when a demo or test writes
  then immediately reads, poll for the actual expected condition instead
  of guessing a fixed sleep duration; this pattern generalizes well beyond
  Pinecone.
- **`.env.example` is a git-tracked file, not a secrets file** — it should
  only ever contain placeholder values. A real secret pasted into it, even
  briefly, is worth catching and fixing immediately, before it's ever
  staged or committed.
