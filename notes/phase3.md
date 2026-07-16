# 📘 Phase 3 — Embeddings + Vector Search with Pinecone

> A simple learning journal for Phase 3 of MemoryRAG. Written in plain,
> beginner-friendly language — meant to be pasted straight into Notion.

## TL;DR — what did we actually make?

Search by **meaning**, not exact words. You upload some text, it gets split
into chunks and turned into number-lists (**embeddings**) that capture what
it *means*, and saved into **Pinecone** — a hosted (cloud) vector database.
Later you can ask a question in your own words — not the original wording —
and still get back the right chunk.

We proved it with `demo/demo_phase3.py`: uploaded a paragraph about a
made-up topic (Glimmerwood squirrels) plus an unrelated made-up decoy (a
kite tournament), then asked a question that **completely paraphrases** the
source text with zero shared words — and the squirrel chunk still won every
time. That's the real proof this is semantic search, not keyword matching.

This phase was first built with Chroma (a local vector database), then
rebuilt to use **Pinecone** (a hosted one) instead — see below for why that
swap was easy, and for a real, surprising bug we hit along the way.

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/embeddings/chunking.py` | Splits a long piece of text into smaller, slightly-overlapping pieces |
| `backend/embeddings/model.py` | Loads the embedding model once, turns text into number-vectors |
| `backend/embeddings/store.py` | Creates/talks to the Pinecone index — upserts and searches vectors |
| `backend/api/documents.py` | The `/documents/upload` and `/documents/search` web addresses |
| `backend/schemas.py` | Now also describes upload/search request & response shapes |
| `demo/demo_phase3.py` | Uploads a real doc + a decoy doc, then proves paraphrased search still finds the right one |
| `.env.example` | Now also documents `PINECONE_API_KEY` |

For the deep, line-by-line version of every file above, see
[`phases/phase3.md`](../phases/phase3.md) — this note is the "story and
summary" version, that one is the "read every line" version.

---

## 🧠 New words explained super simply

- **Embedding** — turning text into a long list of numbers that captures
  its *meaning*. Similar meanings → similar-looking numbers, even with
  completely different words.
- **Vector database** — a database built to answer "which saved number-lists
  are closest in meaning to this new one?" We used **Pinecone**.
- **Hosted / serverless** — Pinecone runs entirely on Pinecone's own
  servers, not on your machine. Unlike Postgres in Phase 1, there's nothing
  to install or start locally — just an API key.
- **Index** — Pinecone's version of "a database." Has a fixed size (how
  many numbers per vector) and a fixed way of measuring "closeness," both
  set once at creation time.
- **Namespace** — a labeled "drawer" inside one index, letting you keep
  different groups of vectors separate without needing a whole separate
  index for each group.
- **Upsert** — Pinecone's word for "save this" (update it if it already
  exists, insert it fresh if it doesn't).
- **Chunking** — cutting a long document into smaller pieces before
  embedding, so search results come back as focused paragraphs, not entire
  documents.
- **Overlap** — letting neighboring chunks share a little text at their
  edges, so an idea that falls right on a cut point still appears whole in
  at least one chunk.
- **Semantic search** — search by meaning, not exact word matches. This
  whole phase exists to prove this actually works.
- **Cosine similarity score** — a number saying how close two pieces of
  text are in meaning. With Pinecone's cosine metric, **higher** means
  **more** similar (the opposite of a "distance," where lower would be
  closer).
- **Eventual consistency** — a property of many hosted databases where,
  right after you write new data, reading it back *immediately* isn't
  100% guaranteed to reflect it correctly yet — it usually catches up
  within moments. We hit a real example of this — see below.

---

## 🛠️ The setup story — what we ran, and every bump along the way

1. **Signed up for a free Pinecone account** at pinecone.io and got an API
   key — added it to `.env` (never committed) and `.env.example` (as a
   placeholder only).

2. **First built this phase with Chroma** (a local, file-based vector
   database) — it worked, but the prompt was updated to specifically use
   Pinecone instead, a *hosted* vector database, so the storage layer was
   rebuilt.

3. **The rebuild only touched one file.** Because `backend/api/documents.py`
   only ever talks to two functions — `add_chunks()` and `search()` — from
   `backend/embeddings/store.py`, swapping the entire vector database
   underneath meant rewriting *just* `store.py`. Nothing else in the app
   needed to change. This is the payoff of keeping a clean boundary between
   "the API" and "which specific database happens to be behind it."

4. **A real secret-leak near-miss.** While setting up `.env`, a real
   Pinecone API key briefly ended up pasted into `.env.example` too —
   which matters because `.env.example` (unlike `.env`) is **not**
   gitignored; it's meant to be committed with placeholder values only. We
   caught this, confirmed it had never actually been committed to git
   history, and restored the placeholder immediately. **Takeaway:** always
   double check *which* file a secret went into — `.env` and `.env.example`
   look similar but have completely different git treatment.

5. **First live run against the real Pinecone account — a genuine, subtle
   bug.** Testing end-to-end for real (not just reasoning through the
   code), the demo occasionally ranked the *wrong* document first — the
   unrelated kite-tournament chunk beat the correct squirrel chunk, even
   though the squirrel chunk's own score was clearly higher (like `0.81`
   vs. `0.47` — not a close call). Tracked down by querying Pinecone
   directly, bypassing our own code entirely, and reproducing the exact
   same wrong order — proving it wasn't a bug in *our* code, but in the
   timing of the request itself.

6. **The real cause: Pinecone serverless's "eventual consistency."**
   Immediately after the very first upserts into a brand-new namespace,
   Pinecone's index can take a short — but sometimes surprisingly long
   (observed up to about a minute!) — while to fully "settle" before
   search reliably reflects what was just written. A fixed `sleep(5)`
   wasn't reliably long enough.

7. **The fix:** instead of guessing a sleep duration, `demo/demo_phase3.py`
   now **polls** — it repeatedly re-runs one known "canary" search (up to a
   60-second cap) until the expected correct answer actually shows up, then
   proceeds with the real demonstration queries. Re-ran the full demo
   afterward — passed cleanly, with the settle-check confirming quickly.

8. **Also spot-checked the file-upload path** (as opposed to raw text) with
   a real `.txt` file — correctly stored the real filename as metadata and
   was retrievable by a paraphrased query.

---

## 🧪 How to try it yourself

### Terminal 1 — start the server

```bash
conda activate memoryrag
export DATABASE_URL="postgresql+psycopg2://<your-mac-username>@localhost:5432/memoryrag"
export SECRET_KEY="some-long-random-string"
export PINECONE_API_KEY="your-real-pinecone-key"
uvicorn backend.main:app --reload --port 8010
```

The very first time you run this against a fresh Pinecone account, the app
will create the `memoryrag` index automatically — that's expected and only
happens once.

### Terminal 2 — run the demo

```bash
python3 demo/demo_phase3.py http://localhost:8010
```

Expect the first run to take a bit longer (downloading the embedding model,
plus the settle-check polling after upload). You'll see both documents get
uploaded, a short "waiting for the index to settle" message, then each
search query printed with its results and scores, ending in a message
confirming every query correctly ranked the relevant chunk above the
unrelated one.

### Or, by hand in Swagger UI (`http://localhost:8010/docs`)

1. **`POST /documents/upload`** → "Try it out" → set `project_id` to any
   number, put a paragraph of your own choosing (pick something made up, so
   you can be sure any correct answer really came from your text) into
   `text`, leave `file` empty → Execute.
2. **Wait 10–20 seconds** before searching — this gives Pinecone's index
   time to settle on freshly-written data (see the eventual-consistency
   story above).
3. **`POST /documents/search`** → "Try it out" → ask a question about your
   paragraph, but **in your own words** — don't copy a sentence directly.
   You should still get your chunk back.
4. Try uploading a second, totally different paragraph, then search again
   — you should see whichever paragraph actually matches your question rank
   first.

---

## ✅ What to remember going forward

- **Embeddings are how "search by meaning" becomes possible** — text gets
  converted into numbers that capture meaning, not just spelling.
- **Chunk before embedding**, with a bit of overlap, so search results come
  back as focused, relevant pieces rather than whole documents, and no idea
  gets awkwardly split in half at a chunk boundary.
- **Load big models once, not per-request** — a lazy singleton pattern
  keeps the app fast after that first slow load.
- **Always test search against a decoy, not just one document.** A search
  that only ever has one possible answer to return proves nothing about
  whether the ranking logic actually works.
- **Use made-up topics when testing semantic search claims** — otherwise
  you can't tell whether a correct answer came from your uploaded text or
  from something the model already knew from its own training.
- **A hosted database can be briefly "eventually consistent" right after a
  write** — if a test writes then immediately reads, poll for the real
  expected result instead of guessing a fixed sleep duration.
- **Keep API code decoupled from a specific database.** Swapping the entire
  vector database (Chroma → Pinecone) only required rewriting one file,
  because the rest of the app only ever talked to two small functions,
  never to the database library directly.
- **`.env.example` is committed to git — never let a real secret sit in it,
  even briefly.** Only `.env` itself is gitignored.
