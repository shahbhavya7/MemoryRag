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
`postgresql+psycopg2://<your-username>@localhost:5432/memoryrag` (no password).

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
python demo_phase1.py
```

It prints every request and response so you can verify each step against a live database.
