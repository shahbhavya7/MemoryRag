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
