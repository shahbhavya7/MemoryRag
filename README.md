# MemoryRAG

## Phase 1: FastAPI + PostgreSQL skeleton

### 1. Start PostgreSQL

Option A — Docker:

```bash
docker-compose up -d
```

This starts Postgres 16 on `localhost:5432` with database `memoryrag` (user/password: `postgres`/`postgres`).

Option B — local Homebrew Postgres (used to verify this phase):

```bash
brew install postgresql@16
brew services start postgresql@16
createdb memoryrag
```

Homebrew's Postgres uses trust auth for your OS user, so `DATABASE_URL` becomes
`export DATABASE_URL="postgresql+psycopg2://bhavya@localhost:5432/memoryrag"` (no password).
`export SECRET_KEY="dev-secret-please-change-me"`

### 2. Install dependencies

Using conda:

```bash
conda create -n memoryrag python=3.12
conda activate memoryrag
pip install -r requirements.txt
```

Or with a standard venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust `DATABASE_URL` if needed:

```bash
cp .env.example .env
```

### 3. Run the API

```bash
uvicorn backend.main:app --reload
```

Tables are created automatically on startup. The API is now available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### 4. Run the demo

With the API running in one terminal, run the demo script in another to exercise the full CRUD lifecycle (create → list → get → update → delete → confirm 404):

```bash
python demo/demo_phase1.py
```

It prints every request and response so you can verify each step against a live database.

## Phase 2: Multi-user auth (JWT)

Adds `User` and `Chat` tables, JWT-based login, and locks down the Project/Chat routes so only logged-in users can call them.

### New endpoints

| Method | Path                              | Auth required | Description                                  |
|--------|------------------------------------|----------------|-----------------------------------------------|
| POST   | `/auth/register`                   | No             | Create a user (`email`, `password`)           |
| POST   | `/auth/login`                      | No             | Log in, returns `{access_token, token_type}`  |
| POST   | `/projects`                        | Yes            | (existing, now protected)                     |
| GET    | `/projects`                        | Yes            | (existing, now protected)                     |
| GET/PUT/DELETE | `/projects/{project_id}`   | Yes            | (existing, now protected)                     |
| POST   | `/projects/{project_id}/chats`     | Yes            | Create a chat under a project                 |
| GET    | `/projects/{project_id}/chats`     | Yes            | List your chats for a project                 |
| GET/PUT/DELETE | `/projects/{project_id}/chats/{chat_id}` | Yes | Get / rename / delete a chat you own |

All protected routes expect an `Authorization: Bearer <token>` header. A missing or invalid token returns `401`.

### 1. Install the extra dependencies

```bash
pip install -r requirements.txt
```

This adds `passlib` + `bcrypt` (password hashing) and `python-jose` (JWT tokens).

### 2. Set a `SECRET_KEY`

Copy `.env.example` to `.env` if you haven't already, and set a `SECRET_KEY` (any random string works for local dev — this is what signs your JWTs):

```bash
cp .env.example .env
```

Then export the values before running the server (the app reads them from the environment, not from `.env` directly):

```bash
export DATABASE_URL="postgresql+psycopg2://<your-username>@localhost:5432/memoryrag"
export SECRET_KEY="some-long-random-string"
```

### 3. Run the API

```bash
uvicorn backend.main:app --reload
```

The new `users` and `chats` tables are created automatically alongside `projects`.

### 4. Run the demo

```bash
python demo/demo_phase2.py
```

It registers a throwaway user, logs in, creates a project, creates a chat under that project, lists chats, and finally confirms that calling `/projects` with no token returns `401`.

## Phase 3: Embeddings + vector search (Pinecone)

Adds semantic document search: upload text, it gets chunked and embedded, and you can search it by meaning instead of exact keywords. Vectors are stored in **Pinecone**, a hosted/serverless vector database — no local vector store, no docker-compose changes.

### 1. Get a free Pinecone API key

Sign up for a free account at [pinecone.io](https://www.pinecone.io) (the free "Starter" plan is enough for this project) and copy your API key.

Copy `.env.example` to `.env` and fill in `PINECONE_API_KEY`:

```bash
cp .env.example .env
```

Then export it before running the server (the app reads from the environment, not from `.env` directly):

```bash
export PINECONE_API_KEY="your-real-key-here"
```

### 2. Index creation (automatic, one-time)

On startup, the app checks whether a serverless index named `memoryrag` (dimension 384, to match `BAAI/bge-small-en-v1.5`; metric `cosine`) already exists in your Pinecone account, and creates it if not. This check is guarded — it's safe to restart the app any number of times; the index is only ever created once and reused on every later run.

We'll use additional **namespaces** within this same index (not separate indexes) for the other memory types added in Phase 5 — keeping everything on one index is important because Pinecone's free tier caps how many serverless indexes you can have, but namespaces within an index are effectively free and keep each memory type's vectors isolated from the others.

The first request that touches embeddings (upload or search) will also download the `BAAI/bge-small-en-v1.5` model (~130MB) from Hugging Face and cache it under `~/.cache/huggingface`. That first request will be noticeably slower; every request after that is fast.

### New endpoints

| Method | Path                | Auth required | Description                                                       |
|--------|---------------------|----------------|---------------------------------------------------------------------|
| POST   | `/documents/upload` | No             | Upload raw `text` or a `file` (multipart form), chunked + embedded |
| POST   | `/documents/search`  | No            | `{query, top_k}` — returns the most semantically similar chunks     |

`/documents/upload` takes multipart form fields: `project_id` (int), and either `text` (string) or `file` (a text file upload) — not both.

Search results' `score` is Pinecone's cosine similarity: **higher means more similar** (this is the opposite convention from a "distance," where lower would mean closer).

### 3. Install the extra dependencies

```bash
pip install -r requirements.txt
```

This adds `pinecone` (hosted vector database client), `sentence-transformers` (embedding model), and `python-multipart` (needed for file uploads in FastAPI).

### 4. Run the API

```bash
export DATABASE_URL="postgresql+psycopg2://<your-username>@localhost:5432/memoryrag"
export SECRET_KEY="some-long-random-string"
export PINECONE_API_KEY="your-real-key-here"
uvicorn backend.main:app --reload
```

### 5. Run the demo

```bash
python demo/demo_phase3.py
```

It uploads a made-up-topic document (Glimmerwood squirrels) plus an unrelated distractor document (a kite tournament), then runs several search queries — including one that fully paraphrases the source text with no shared keywords — and confirms the relevant squirrel chunk always ranks above the unrelated one, proving the search is genuinely semantic rather than keyword matching.

## Phase 4: Basic RAG chat (LangChain + LLM)

Wires up a simple **RAG** (Retrieval-Augmented Generation) chat: embed the question → retrieve the most relevant chunks *for that project* → build a prompt with those chunks → call an LLM → return the answer plus the sources it was grounded in. No memory routing yet (that's Phase 5+) — this is a single-collection RAG baseline.

### 1. Get an LLM API key

Set an OpenAI-compatible LLM provider via env vars. Two supported out of the box:

- **Groq** (free, fast) — get a key at [console.groq.com/keys](https://console.groq.com/keys)
- **OpenRouter** — get a key at [openrouter.ai/keys](https://openrouter.ai/keys)

In `.env`:

```bash
LLM_PROVIDER=groq          # or: openrouter
LLM_API_KEY=your-real-key
# LLM_MODEL=...             # optional; sensible per-provider default is used if unset
```

Both providers expose OpenAI-compatible APIs, so a single LangChain `ChatOpenAI` client handles either — only the base URL and key change.

### New endpoint

| Method | Path    | Auth required | Description                                                  |
|--------|---------|----------------|--------------------------------------------------------------|
| POST   | `/chat` | No             | `{project_id, message}` → `{answer, sources: [...]}`         |

Retrieval is scoped to the given `project_id`, so a chat only ever sees that project's own documents. Each exchange (your message + the assistant's answer) is logged to the `messages` table.

### 2. Install the extra dependency

```bash
pip install -r requirements.txt
```

This adds `langchain-openai` (the LangChain LLM client + prompt/chain plumbing).

### 3. Run the API and demo

```bash
./run.sh                       # or: uvicorn backend.main:app --reload
python demo/demo_phase4.py     # in a second terminal
```

The demo uploads a short made-up document (the Aurora Tram), asks two questions answerable from it, and prints **both the answer and the exact source chunks used** — so you can see the answer is grounded in the retrieved text. It then asks one question the document *can't* answer, to show the model declines ("I don't know based on the available documents") instead of hallucinating.

## Phase 5: Multi-memory split (five memory types)

Splits the single vector store into **five isolated memory types**, each in its own Pinecone namespace within the same `memoryrag` index:

| Memory type    | Namespace              | Holds |
|----------------|------------------------|-------|
| `document`     | `document_memory`      | PDFs, docs, notes, wiki pages |
| `code`         | `code_memory`          | functions, classes, APIs, READMEs |
| `decision`     | `decision_memory`      | structured engineering decisions |
| `workflow`     | `workflow_memory`      | processes / step-by-step flows |
| `conversation` | `conversation_memory`  | important discussions worth keeping |

Using **namespaces within one index** (rather than five separate indexes) keeps everything on Pinecone's free tier while still isolating each type's vectors completely. Two new Postgres tables track things relationally: `memory_types` (the five reference rows, auto-seeded on startup) and `memories` (each stored entry, linked to its type and to its Pinecone `vector_id`).

There's no memory *routing* yet — you say which type to write/search explicitly. Automatic routing ("which memory should answer this?") is Phase 6.

### New endpoints

| Method | Path               | Description                                                         |
|--------|--------------------|---------------------------------------------------------------------|
| POST   | `/memories`        | `{memory_type, content, source_ref}` → embeds into that type's namespace + logs in Postgres |
| POST   | `/memories/search` | `{memory_type, query, top_k}` → searches **only** that type's namespace |

### Seed + prove isolation

```bash
./run.sh                          # start the API (memory_types auto-seed on startup)
python demo/seed_phase5.py        # optional: seed 2-3 example entries per type
python demo/demo_phase5.py        # seeds its own entries, then proves isolation
```

`demo_phase5.py` runs a 5×5 matrix: it searches *every* namespace with *every* type's query and confirms each namespace only ever returns its own type — even when the query semantically matches a different type's content. That proves the types are structurally isolated, not merely labeled.

## Phase 6: LangGraph + Adaptive Memory Routing

The core of the project. `/chat` is now a **LangGraph agent** that decides *which* memory type(s) a question needs, retrieves only from those, and answers — instead of always searching one collection.

The graph has eight nodes, run in order:

```
receive_query → intent_detection → memory_router → retriever
   → re_ranker → context_builder → llm_response → memory_update
```

- **intent_detection** — an LLM classifier picks one or more of `[document, code, decision, workflow, conversation]`.
- **memory_router** — turns those types into the Pinecone namespace(s) to search.
- **retriever** — queries only the selected namespace(s).
- **re_ranker** — merges hits from multiple namespaces and sorts by score.
- **context_builder** — assembles the prompt with a hard character-limit truncation (Phase 7 makes this smarter).
- **llm_response** — generates the grounded answer.
- **memory_update** — if the user's message *states* a new decision/fact (not just asks), writes it back to the right memory type.

`/chat` `{project_id, message}` now returns `{answer, memory_types, sources, memory_update}` — where `memory_types` is the router's decision (the proof point for this phase).

### Prove the routing

```bash
./run.sh
python demo/demo_phase6.py
```

`demo_phase6.py` seeds one distinctive entry per memory type, then asks five questions — each aimed at a different type (a "why did we choose X" → decision, a "how do we release" → workflow, etc.) — and prints **which memory type the router picked** for each, asserting all five route correctly. A bonus step then *states* a new decision and shows the `memory_update` node saving it back to `decision` memory.

## Phase 7: Prompt versioning + context engineering + evaluation

Three upgrades to make the system tunable and *measurable*:

**1. Versioned prompts** (`backend/prompts/`). The classifier prompt now lives in files (`classifier_v1.txt`, `classifier_v2.txt`), selected via `CLASSIFIER_PROMPT_VERSION` (default `v2`). Change the prompt without touching code, and A/B different versions.

**2. Real context engineering** ([backend/llm/context.py](backend/llm/context.py)). The old blunt character-limit truncation is replaced with **token counting** (`tiktoken`) and a **token budget** (`CONTEXT_TOKEN_BUDGET`, default 1200) split across *system prompt / conversation history / retrieved context*. History and chunks are fit into their share; the lowest-scored chunks are dropped first when space runs out.

**3. Evaluation** — a real routing-accuracy metric, not a vibe check.

### New endpoint

| Method | Path                          | Description |
|--------|-------------------------------|-------------|
| GET    | `/context-trace/{message_id}` | For a given chat answer: what was retrieved, what was **kept vs. dropped**, and the token breakdown (system/history/context/total) |

Every `/chat` response now includes a `message_id`; pass it to `/context-trace/{message_id}` to see exactly what the LLM was (and wasn't) given.

### Run the evaluation

```bash
set -a; source .env; set +a        # eval needs LLM_API_KEY
python demo/eval_phase7.py
```

`eval_phase7.py` runs 10 hand-labeled `question → expected memory type` pairs through the router and prints **routing accuracy** — for *both* prompt versions, so you can see as a number whether a prompt change actually helped. This is the project's first real retrieval-quality metric. (Routing uses an LLM classifier, so exact numbers vary slightly run to run.)

## Phase 8: Git integration → Code Memory

Real **commit history** becomes searchable memory. Point MemoryRAG at a local git repo; it walks the commit log, turns each commit (message + a capped diff) into text, embeds it, and stores it in **code memory** — and additionally in **decision memory** when the commit message reads like it explains a *why* (e.g. "we switched to X because…"). Every entry's `source_ref` is the **commit hash**, so an answer can cite the exact commit(s) it came from.

Built with **GitPython**. The storage path is the same shared `store_memory` writer from Phase 5 — Phase 8 only adds a new *source* of memories.

### New endpoint

| Method | Path          | Description |
|--------|---------------|-------------|
| POST   | `/ingest/git` | `{repo_path, max_commits?, branch?}` → walks the repo's commits into code (+ decision) memory; returns a per-commit summary. Bad path → clear 400. |

### CLI (same logic, no server)

```bash
set -a; source .env; set +a
python -m backend.services.git_ingest <repo_path> [--max-commits N] [--branch NAME]
```

### Demo

```bash
./run.sh                              # start the API
python demo/demo_phase8.py http://localhost:8010
```

`demo_phase8.py` ingests **this project's own git history**, then asks a few "what changed…" / "what was done…" questions and prints each answer **plus the commit hash(es) it cited**.

> ⚠️ Git diff chunks are large (~800 tokens each). For grounded answers, run with a healthy `CONTEXT_TOKEN_BUDGET` (e.g. `1500`–`2000`). With a tiny budget a whole commit won't fit the context slice, and answers fall back to "I don't know" — that's the Phase 7 token budget doing its job, not a Phase 8 bug.
