# Phase 1 — FastAPI + PostgreSQL Skeleton

Goal of this phase: stand up the smallest possible real backend — one
database-backed entity (`Project`), full CRUD REST endpoints for it, a health
check, and proof (a live demo script) that it actually works end to end.

This file explains **every file that exists in this phase**, **what every
function in it does and why it's written that way**, and **every terminal
command that was run to get it working**, including the detours (Docker
rejected, conda ToS, port conflicts) and why each fix was the right one.

---

## 1. Folder structure created in this phase

```
MemoryRag/
├── backend/
│   ├── __init__.py            # makes `backend` an importable Python package
│   ├── main.py                 # FastAPI app entrypoint
│   ├── schemas.py              # Pydantic request/response models
│   ├── api/
│   │   ├── __init__.py
│   │   └── projects.py         # /projects CRUD routes
│   ├── database/
│   │   ├── __init__.py
│   │   └── session.py          # DB engine, session factory, Base class
│   └── models/
│       ├── __init__.py
│       └── project.py           # SQLAlchemy ORM model for the `projects` table
├── demo_phase1.py               # scripted CRUD walkthrough against the live API
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

Why split into `api/` / `database/` / `models/` instead of one big file?
Each folder has one job — `models` describes tables, `database` describes how
we talk to Postgres, `api` describes HTTP routes, `schemas.py` describes the
shape of data crossing the HTTP boundary. This mirrors how real FastAPI
projects are laid out (and matches the folder structure your `CLAUDE.md`
already committed to for later phases), so adding Decision/Workflow/Code
memories later just means adding more files in the same pattern, not
restructuring.

---

## 2. File-by-file, function-by-function breakdown

### `backend/database/session.py` — the database connection layer

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/memoryrag"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- **`DATABASE_URL = os.getenv(...)`** — reads the connection string from the
  environment, falling back to a sane local default. This is why the task
  said "read `DATABASE_URL` from env, with a `.env.example`" — hardcoding
  credentials in source is both a security smell and makes the app
  un-deployable without editing code. `postgresql+psycopg2://` tells
  SQLAlchemy which database dialect (`postgresql`) and which driver
  (`psycopg2`) to use to actually speak to it.
- **`engine = create_engine(DATABASE_URL)`** — the `engine` is SQLAlchemy's
  connection pool manager. It doesn't open a connection immediately; it opens
  one lazily the first time you actually query.
- **`SessionLocal = sessionmaker(...)`** — a *factory* for `Session` objects.
  A `Session` is your actual conversation with the database for one unit of
  work (one request, in our case). `autocommit=False` means nothing is
  written until you call `.commit()` explicitly — this is what lets us
  control exactly when a create/update/delete becomes permanent.
- **`Base = declarative_base()`** — every ORM model (like `Project`) inherits
  from this. It's the glue that lets SQLAlchemy turn a Python class into a
  SQL table definition, and later collect all such classes under
  `Base.metadata` so `create_all()` knows what tables to make.
- **`def get_db():`** — a *generator function* used as a FastAPI dependency.
  `yield db` hands the session to whichever endpoint asked for it; execution
  pauses there for the duration of the request. Once the endpoint function
  returns, control comes back here and `db.close()` runs in the `finally`
  block — guaranteeing the connection is released even if the endpoint threw
  an exception. This "yield, then cleanup after" shape is FastAPI's standard
  pattern for anything that needs setup + guaranteed teardown per-request
  (DB sessions, file handles, locks).

### `backend/models/project.py` — the ORM model (the table's Python shape)

```python
from sqlalchemy import Column, DateTime, Integer, String, func
from backend.database.session import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- **`class Project(Base):`** — inheriting from `Base` registers this class in
  `Base.metadata`, so SQLAlchemy knows "there should be a table called
  `projects` with these columns."
- **`__tablename__ = "projects"`** — the actual SQL table name. Plural by
  convention.
- **`id = Column(Integer, primary_key=True, index=True)`** — the primary key.
  Postgres auto-increments this by default when it's an `Integer` primary
  key under SQLAlchemy. `index=True` builds a B-tree index for fast lookups
  by id (which we do constantly — every GET/PUT/DELETE by id uses it).
- **`name`, `description`** — `nullable=False` on `name` means Postgres will
  reject any insert without a name at the database level, as a second line of
  defense under the Pydantic validation in `schemas.py`.
- **`created_at = Column(DateTime(timezone=True), server_default=func.now(), ...)`**
  — `server_default=func.now()` means *Postgres itself* stamps the current
  time on insert (via SQL `now()`), not Python. This is deliberate: it's
  correct even if multiple app servers with clock drift are inserting rows,
  and it means we never have to remember to set `created_at` manually when
  creating a project.

### `backend/schemas.py` — Pydantic models (the HTTP-facing shape of a Project)

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    name: str
    description: str | None = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
```

This is one of the most important concepts in the whole app: **the ORM model
(`Project`) and the API schema (`ProjectOut` etc.) are deliberately two
different classes**, even though they look similar. The ORM model describes a
database row. The Pydantic schema describes JSON going over HTTP. Keeping
them separate means:
- Clients can never set `id` or `created_at` on create/update — those fields
  simply don't exist on `ProjectCreate`/`ProjectUpdate`, so if someone POSTs
  `{"id": 999, ...}`, Pydantic silently ignores the extra field rather than
  letting a client fake an id or timestamp.
- We can reshape what's exposed to clients independently of what's stored,
  which matters more as memory types get more complex in later phases.

- **`ProjectBase`** — the fields every variant shares: `name` (required
  string) and `description` (optional, defaults to `None` via `str | None`).
- **`ProjectCreate` / `ProjectUpdate`** — currently identical to `ProjectBase`
  (`pass` means "no changes, just reuse the parent"). They're kept as
  separate classes on purpose even though they're identical today, because in
  a real app they usually diverge (e.g., `ProjectUpdate` might make every
  field optional for partial updates) — having the two names already in place
  means that future change touches one class, not every endpoint signature.
- **`ProjectOut`** — what the API sends *back*. Adds `id` and `created_at`,
  which only exist once a row is actually in the database.
- **`model_config = ConfigDict(from_attributes=True)`** — this is the part
  that makes it possible to write `return project` in an endpoint where
  `project` is a SQLAlchemy `Project` object, not a dict. Normally Pydantic
  only builds a model from a dict-like object; `from_attributes=True` tells
  it "also allow reading fields off a plain Python object via attribute
  access" (i.e. `project.id`, `project.name`, ...), which is exactly what a
  SQLAlchemy row is.

### `backend/api/projects.py` — the actual CRUD endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.project import Project
from backend.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])
```

- **`APIRouter(prefix="/projects", tags=["projects"])`** — a mini FastAPI app
  that only knows about `/projects/...` routes. `prefix` means every route
  below is automatically mounted under `/projects` (so `@router.get("")` is
  really `GET /projects`). `tags` is purely cosmetic — it groups these routes
  under a "projects" heading in the auto-generated `/docs` page.

```python
def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

- A private helper (leading underscore = "internal to this module, not part
  of the public API"). `db.get(Project, project_id)` is SQLAlchemy 2.0's
  primary-key lookup — equivalent to `SELECT * FROM projects WHERE id = :id`.
  Raising `HTTPException(404, ...)` here means GET/PUT/DELETE all get
  identical "not found" behavior for free, instead of repeating the same
  `if project is None: raise ...` three times.

```python
@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
```

- **`payload: ProjectCreate`** — FastAPI reads the request's JSON body,
  validates it against `ProjectCreate` (rejecting the request with a 422 if
  `name` is missing, for instance), and hands you a real Python object. You
  never manually parse JSON.
- **`db: Session = Depends(get_db)`** — this is FastAPI's *dependency
  injection*. `Depends(get_db)` tells FastAPI "before running this endpoint,
  call `get_db()`, run it up to its `yield`, and pass that value in as `db`."
  After the endpoint returns, FastAPI resumes `get_db()` past the `yield`,
  running `db.close()`. Every request gets its own session, and it's always
  closed — you never have to remember to do it in the endpoint body.
- **`Project(**payload.model_dump())`** — `payload.model_dump()` turns the
  Pydantic object into a plain dict (`{"name": ..., "description": ...}`),
  and `**` unpacks it as keyword arguments into the `Project(...)`
  constructor. This is why `ProjectCreate` and `Project`'s columns need
  matching field names.
- **`db.add(project)`** — stages the new row in the session (nothing hits
  Postgres yet).
- **`db.commit()`** — sends the actual `INSERT` and commits the transaction.
  This is the moment the row becomes real and Postgres assigns `id` and
  `created_at` (via `server_default=func.now()`).
- **`db.refresh(project)`** — after commit, the Python object still doesn't
  know the `id`/`created_at` Postgres generated. `refresh` re-fetches the row
  from the database into the same object so we can return a complete
  `ProjectOut` (with a real id and timestamp) in the response.
- **`status_code=201`** — REST convention: `201 Created` for a successful
  POST that creates a resource, not `200`.

```python
@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id).all()
```
- `order_by(Project.id)` guarantees a stable, predictable order (`ORDER BY id`
  in SQL) instead of whatever order Postgres feels like returning rows in.

```python
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _get_project_or_404(db, project_id)
```
- `{project_id}` in the path is a *path parameter* — FastAPI extracts it from
  the URL and, because the function signature types it as `int`, also
  validates/converts it (a non-numeric id in the URL gets an automatic 422).

```python
@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    for field, value in payload.model_dump().items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project
```
- Fetches the existing row (404s if missing), then loops over every field in
  the incoming payload and uses `setattr` to overwrite it on the live ORM
  object. SQLAlchemy tracks that the object is "dirty" and generates an
  `UPDATE` statement on `commit()` — you never write raw SQL for this.
  (This endpoint does a *full* replace of `name`/`description`, matching
  `PUT`'s REST semantics — as opposed to `PATCH`, which would do a partial
  update.)

```python
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
```
- `status_code=204` = "No Content" — the REST-correct response for a
  successful delete with nothing to return. Notice there's no `return`
  statement; FastAPI sends an empty body, which is why the demo script's
  `show()` helper checks `if response.content:` before calling
  `.json()` on it.

### `backend/main.py` — the app entrypoint

```python
from fastapi import FastAPI
from backend.api.projects import router as projects_router
from backend.database.session import Base, engine
from backend.models import project  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MemoryRAG API", version="0.1.0")
app.include_router(projects_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```
- **`from backend.models import project  # noqa: F401`** — this import looks
  unused (nothing in this file calls anything from it), but it's essential:
  importing the module runs `class Project(Base): ...`, which registers the
  table on `Base.metadata`. Without this import, `Base.metadata` would be
  empty and `create_all` would create zero tables. The `# noqa: F401` comment
  tells linters "yes, I know this import looks unused, don't flag it."
- **`Base.metadata.create_all(bind=engine)`** — inspects every model
  registered on `Base` and issues `CREATE TABLE IF NOT EXISTS ...` for any
  that don't already exist. This runs once at import time (i.e. once per
  server start), which is why you don't need a separate migration step in
  Phase 1 — good enough until the schema needs to *change* under existing
  data, which is what a tool like Alembic would handle in a later phase.
- **`app.include_router(projects_router)`** — mounts every route defined in
  `projects.py` onto the main app, under the `/projects` prefix set on the
  router.
- **`GET /health`** — the simplest possible liveness check: if this responds
  200, the process is up and able to serve HTTP. It deliberately does *not*
  touch the database, so it also tells you "the web server is fine" even if
  Postgres is having a bad day — useful for load balancers/orchestrators that
  just want to know "should I send traffic here."

### `demo_phase1.py` — proof the whole stack works

```python
import sys
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

def show(label, response):
    print(f"\n--- {label} ---")
    print(f"{response.request.method} {response.request.url} -> {response.status_code}")
    if response.content:
        print(response.json())
```
- Takes the base URL as an optional command-line argument (`sys.argv[1]`) so
  it can point at any port — this is exactly why we could run it against
  `http://localhost:8010` when port 8000 turned out to be taken.
- `show()` is a tiny reporting helper: every step of the demo prints the HTTP
  method, full URL, status code, and body, so a human reading the terminal
  output can verify each step visually rather than trusting a silent pass/fail.

```python
def main():
    health = requests.get(f"{BASE_URL}/health"); show(...); health.raise_for_status()
    created = requests.post(f"{BASE_URL}/projects", json={...}); show(...); created.raise_for_status()
    project_id = created.json()["id"]
    listed = requests.get(f"{BASE_URL}/projects"); ...
    fetched = requests.get(f"{BASE_URL}/projects/{project_id}"); ...
    updated = requests.put(f"{BASE_URL}/projects/{project_id}", json={...}); ...
    deleted = requests.delete(f"{BASE_URL}/projects/{project_id}"); ...
    confirm_404 = requests.get(f"{BASE_URL}/projects/{project_id}")
    assert confirm_404.status_code == 404, "Expected 404 after delete"
```
- `raise_for_status()` after every call means the script *stops immediately*
  with a clear Python traceback the moment any step returns a 4xx/5xx it
  didn't expect — instead of silently continuing with garbage data.
- The final `assert` is the one place we *expect* a non-2xx response
  (404 after delete) — proving the delete actually took effect, not just that
  the delete call itself succeeded.
- Extracting `project_id = created.json()["id"]` and reusing it through
  get/update/delete proves the id round-trips correctly through Postgres
  (auto-increment → returned in response → usable in subsequent URLs).

### `requirements.txt`, `.env.example`, `docker-compose.yml`

- **`requirements.txt`** pins exact versions (`fastapi==0.115.6`, etc.)
  rather than ranges, so "works on my machine" also means "works on your
  machine" — no surprise upgrades.
- **`.env.example`** documents the one environment variable the app needs
  (`DATABASE_URL`) without committing real credentials — you copy it to
  `.env` and fill in your actual values.
- **`docker-compose.yml`** defines a `postgres:16` service with a named
  volume (`memoryrag_pgdata`) so data survives container restarts, and a
  `healthcheck` using `pg_isready` so other tooling can wait for Postgres to
  actually be ready to accept connections, not just for the container to have
  started.

---

## 3. Every command run to get this working, and why

### Database: why we ended up on Homebrew Postgres instead of Docker

You rejected `docker compose up -d` and asked to install the Postgres version
needed directly instead. That meant:

```bash
brew install postgresql@16
```
Installs Postgres 16 itself plus its CLI tools (`psql`, `createdb`,
`pg_isready`, ...) via Homebrew, matching the version pinned in
`docker-compose.yml` so behavior is consistent either way you run it.

```bash
brew services start postgresql@16
```
Registers Postgres as a background `launchd` service so it starts now *and*
automatically on login — the equivalent of `docker-compose`'s `restart:
unless-stopped`, but for a natively-installed service instead of a container.

```bash
createdb memoryrag
```
Postgres doesn't come with your app's database pre-made — `initdb` only
creates the cluster and a default `postgres` database. `createdb` is a thin
wrapper around `CREATE DATABASE memoryrag;` that makes the actual database
our app connects to.

One consequence worth understanding: Homebrew's `initdb` creates the cluster
owned by your OS user (`bhavya`), not a `postgres` role, and defaults to
**trust authentication** for local connections (no password needed at all).
That's why the working `DATABASE_URL` for local Homebrew Postgres is
`postgresql+psycopg2://bhavya@localhost:5432/memoryrag` — no
`postgres:postgres` — whereas the Dockerized Postgres *does* create a
`postgres` superuser with password `postgres` (because we defined it that way
in `docker-compose.yml`'s `POSTGRES_USER`/`POSTGRES_PASSWORD`). Same app code,
two valid connection strings, depending on which Postgres you're pointed at.

### Python environment: why conda, and the ToS detour

You asked to use conda instead of a plain venv. `conda env list` showed only
`base` existed, so:

```bash
conda create -y -n memoryrag python=3.12
```
This failed the first time with a `CondaToSNonInteractiveError` — conda
now requires you to explicitly accept Anaconda's Terms of Service for its
default channels (`repo.anaconda.com/pkgs/main` and `/pkgs/r`) before it will
install anything from them. This is a legal-acceptance step, so I asked
before running it rather than accepting on your behalf. You chose to accept
the default channels rather than switching to conda-forge:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

Then the env creation succeeded, giving an isolated Python 3.12 install
separate from `base` — so this project's dependency versions can never clash
with anything else you have in `base` or elsewhere.

```bash
conda activate memoryrag
pip install -r requirements.txt
```
Activating switches your shell's `python`/`pip` to point inside the new env;
`pip install -r requirements.txt` then installs FastAPI, Uvicorn, SQLAlchemy,
psycopg2, python-dotenv, and requests *into that env only*.

### The `python` vs `python3` gotcha

Running `python demo_phase1.py` failed with `ModuleNotFoundError: No module
named 'requests'`, even though `pip show requests` proved it was installed —
because your shell has `python` **aliased** directly to
`/usr/local/bin/python3` (visible via `type python` → "python is an alias
for /usr/local/bin/python3"), which bypasses whatever conda env is active.
`python3`, by contrast, resolves through `PATH` normally and correctly picked
up `/opt/miniconda3/envs/memoryrag/bin/python3`. Lesson: after `conda
activate`, always sanity-check with `which python3` (or `python3 -c "import
sys; print(sys.executable)"`) if imports mysteriously fail — an alias can
silently shadow the env you just activated.

### Running the server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
first failed with `[Errno 48] address already in use` — `lsof -nP -iTCP:8000
-sTCP:LISTEN` showed an unrelated Python process already listening on 8000.
Rather than kill a process I didn't start (it might have been your own
work), we just moved our server to an unused port:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8010
```
`backend.main:app` tells Uvicorn "import the `main` module inside the
`backend` package, and run the `app` object inside it" — that `app` is the
`FastAPI()` instance defined in `backend/main.py`.

### Verifying it

```bash
curl -s http://localhost:8010/health
python3 demo_phase1.py http://localhost:8010
```
`curl` is a one-shot manual sanity check. The demo script is the thorough
proof — it's the same lifecycle you'll want to re-run any time you change the
`Project` model or its endpoints, as a fast regression check before moving to
Phase 2.

---

## 4. Concepts to walk away from this phase understanding

- **ORM model vs. Pydantic schema** — one describes storage, one describes
  the wire format. Never assume they must look identical.
- **Dependency injection via `Depends`** — FastAPI's way of giving every
  request its own resource (here, a DB session) with guaranteed cleanup.
- **Session lifecycle**: `add` (stage) → `commit` (persist) → `refresh`
  (pull generated values back into Python).
- **REST status code conventions**: `201` on create, `200` on read/update,
  `204` on delete, `404` when a resource doesn't exist.
- **Why `create_all` is fine for now but won't be forever** — it can create
  new tables, but it will never alter an existing table's columns once data
  exists. A future phase introducing more memory types will likely need a
  real migration tool (e.g. Alembic).
