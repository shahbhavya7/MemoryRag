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
