# Phase 1 — FastAPI + PostgreSQL Skeleton (Beginner Notes)

## What are we even building in this phase?

We're building the smallest possible "real" backend. Not a toy — a backend
that actually saves data in a real database and lets you Create, Read,
Update, and Delete it over the internet (this four-letter combo is called
**CRUD**, and it's the bread and butter of almost every app you've ever used).

The one thing we're storing is called a **Project** — just a name,
a description, and a timestamp of when it was made. It's intentionally
boring. The point of Phase 1 isn't the data, it's proving the *plumbing*
works: app talks to database, database saves things, app can read them back.
Everything in later phases builds on top of this plumbing.

We also wrote a script (`demo/demo_phase1.py`) that automatically clicks
through Create → List → Get → Update → Delete → confirm it's really gone,
so we don't have to trust it blindly — we can *watch* it work.

---

## 1. The folder structure, and why it looks like this

```
MemoryRag/
├── backend/
│   ├── __init__.py            # tells Python "this folder is a package"
│   ├── main.py                 # the front door — starts the app
│   ├── schemas.py              # the shape of data going in/out over the internet
│   ├── api/
│   │   └── projects.py         # the actual web addresses (routes) for Projects
│   ├── database/
│   │   └── session.py          # how we connect to Postgres
│   └── models/
│       └── project.py           # describes the "projects" table in the database
├── demo/
│   └── demo_phase1.py           # a script that tests everything automatically
├── requirements.txt             # list of Python packages this project needs
├── .env.example                 # a template showing what secret settings to fill in
├── docker-compose.yml           # (optional path) a recipe to run Postgres in a container
└── README.md
```

**Why so many small files instead of one big file?** Think of it like a
kitchen: you don't keep the fridge, the stove, and the sink in one drawer.
Each folder has *one job*:
- `models/` = "what does a Project look like as a row in the database?"
- `database/` = "how do we even talk to the database?"
- `api/` = "what web addresses exist, and what do they do?"
- `schemas.py` = "what does a Project look like as JSON, over the internet?"

Splitting things up like this means when Phase 5 adds new memory types
(Decision, Workflow, Code...), we just add more small files following the
same pattern — we don't have to reorganize everything.

---

## 2. Going file by file — what's in each one, in plain words

### `backend/database/session.py` — "how do we connect to Postgres?"

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

Word-by-word, plain-English:

- **`os.getenv("DATABASE_URL", "...")`** — "look for a setting named
  `DATABASE_URL` on this computer (an *environment variable*, which is just a
  named value your operating system remembers for programs to read). If it's
  not there, use this fallback address instead." We do this instead of
  writing the real address directly in the code because (a) passwords
  shouldn't live in code that gets shared/committed, and (b) it lets the
  exact same code connect to a different database on a different computer
  without editing anything.
- **`postgresql+psycopg2://...`** — this whole string is just an address, like
  a URL for a website, but for a database. It says: "use Postgres, talk to it
  using the `psycopg2` translator library, connect as this user, with this
  password, to this database name."
- **`engine = create_engine(...)`** — think of the **engine** as a phone line
  that *can* call the database, but doesn't dial yet. It's set up once and
  reused for the whole app's life.
- **`SessionLocal = sessionmaker(...)`** — a **session** is one actual
  conversation with the database — "hi, save this, now show me that, okay
  I'm done." `sessionmaker` is a machine that makes a fresh session whenever
  we ask for one. `autocommit=False` means: nothing we do actually saves
  permanently until we explicitly say "save it now" (`.commit()`). That's a
  safety net — half-finished work never accidentally becomes permanent.
- **`Base = declarative_base()`** — a blank template. Every table we define
  (like `Project`) will be built by inheriting from this `Base`, which is how
  SQLAlchemy (the library translating Python ↔ SQL for us) keeps track of
  "here are all the tables that should exist."
- **`get_db()`** — this is a little helper that: opens a session, *hands it
  over* (`yield`) to whoever asked for it, waits for them to finish, then
  closes it — no matter what (even if something went wrong, the `finally`
  block guarantees cleanup). FastAPI calls this automatically for every
  request, so every web request gets its own fresh session and it's always
  properly closed afterward. You never have to remember to close it yourself.

### `backend/models/project.py` — "what does a Project look like in the database?"

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

This is called an **ORM model** (ORM = "Object-Relational Mapping" — a fancy
name for "a Python class that secretly *is* a database table"). Instead of
writing raw SQL like `CREATE TABLE projects (...)`, we write a normal-looking
Python class, and SQLAlchemy turns it into a real table for us.

- **`__tablename__ = "projects"`** — the real name of the table inside
  Postgres.
- **`id = Column(Integer, primary_key=True, ...)`** — every row needs a unique
  ID number to tell it apart from every other row. `primary_key=True` says
  "this is that unique ID." Postgres will automatically count up 1, 2, 3...
  for us — we never set it ourselves.
- **`index=True`** — imagine a phone book with no alphabetical order — you'd
  have to read every page to find a name. An **index** is like adding that
  alphabetical order, just for computers, so looking something up by `id`
  (which we do constantly) is fast instead of scanning the whole table.
- **`name = Column(String, nullable=False, ...)`** — a text field.
  `nullable=False` means "this can never be left empty" — Postgres itself
  will refuse to save a Project with no name, as a backup in case our other
  checks (in `schemas.py`) somehow get skipped.
- **`description`** — same idea, but `nullable=True` means it's fine to leave
  this one empty.
- **`created_at`** — `server_default=func.now()` means: "Postgres, you fill
  this in yourself, with the current time, the moment a row is created." We
  don't set it from Python at all — the database is the single source of
  truth for "when was this actually saved," which is more trustworthy than
  trusting every app server's own clock.

### `backend/schemas.py` — "what does a Project look like over the internet?"

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

Here's the single most important idea to take away from this whole file:
**the database version of a Project (`Project` in `models/`) and the
internet version of a Project (these classes here) are two separate
things**, even though they overlap a lot. Why bother separating them?

Imagine if a client could send `{"id": 999, "name": "hi"}` when creating a
project, and we just blindly saved whatever they sent. They could fake an ID,
overwrite someone else's row, or set a fake timestamp. By having a *separate*
"what am I allowed to send in" shape (`ProjectCreate`) that simply doesn't
have an `id` or `created_at` field at all, that kind of mistake becomes
physically impossible — there's no field to put it in.

- **`ProjectBase`** — the fields every version shares: a required `name`
  (must be text) and an optional `description` (`str | None` means "text, or
  nothing at all", defaulting to nothing).
- **`ProjectCreate`, `ProjectUpdate`** — what a client is allowed to send us
  when creating or updating a Project. Right now they're identical to
  `ProjectBase` (the `pass` keyword just means "nothing extra to add"). We
  still keep them as separate names because later on they'll likely need to
  differ (e.g. maybe updates should allow leaving fields out) — and when that
  day comes, we only change one class instead of hunting through every
  endpoint.
- **`ProjectOut`** — what we send *back* to the client. It adds `id` and
  `created_at`, because those only exist once the database has actually
  created the row.
- **`ConfigDict(from_attributes=True)`** — a technical necessity: normally
  Pydantic (the library validating this JSON shape) expects a dictionary like
  `{"name": "x"}`. But what we actually have after a database query is a
  `Project` *object* (`project.name`, not `project["name"]`). This setting
  tells Pydantic "it's fine, just read the values off the object's
  attributes instead of expecting a dictionary."

### `backend/api/projects.py` — "what web addresses exist, and what do they do?"

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.project import Project
from backend.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])
```

A **router** is a mini-collection of related web addresses. `prefix="/projects"`
means every address we define below automatically starts with `/projects` —
so we never have to type that part again. `tags=["projects"]` is purely
cosmetic — it groups these routes together under a "projects" heading on the
docs page you'll see later.

```python
def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

A little helper function (the underscore at the front is a Python convention
meaning "this is just for internal use in this file"). It looks a project up
by id, and if it doesn't exist, it stops everything and sends back a `404`
("Not Found") error — the standard web way of saying "that thing doesn't
exist." Three different endpoints below reuse this instead of repeating the
same "does it exist?" check three times.

```python
@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
```

This function runs whenever someone sends a `POST` request to `/projects`
(POST = "please create something new"). Breaking it down:

- **`payload: ProjectCreate`** — FastAPI automatically reads the incoming
  JSON, checks it matches `ProjectCreate` (rejecting it automatically if,
  say, `name` is missing), and hands it to us as a normal Python object. We
  never have to manually parse JSON ourselves.
- **`db: Session = Depends(get_db)`** — this is **dependency injection**, a
  fancy term for a simple idea: "before running this function, go run
  `get_db()` for me and hand me the result." FastAPI sees `Depends(get_db)`
  and knows to call our `get_db()` helper, grab the session it `yield`s, and
  clean it up afterward automatically — we just get a ready-to-use `db` to
  play with.
- **`Project(**payload.model_dump())`** — `payload.model_dump()` turns the
  incoming data into a plain dictionary. The `**` in front "unpacks" that
  dictionary into individual arguments, so this line is really shorthand for
  `Project(name=payload.name, description=payload.description)`.
- **`db.add(project)`** — "hey session, remember this new row" — but nothing
  is saved to Postgres yet.
- **`db.commit()`** — "okay, actually save it now, for real." This is the
  moment Postgres creates the row and fills in the auto-generated `id` and
  `created_at`.
- **`db.refresh(project)`** — right after `commit()`, our Python object still
  doesn't know what `id`/`created_at` Postgres just picked. `refresh` goes
  back and reads those values into our object so we can send a complete
  answer back to whoever asked.
- **`status_code=201`** — the standard web status code meaning "created
  successfully" (as opposed to the generic `200 OK`).

```python
@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id).all()
```

Runs on `GET /projects` — "give me every project." `order_by(Project.id)`
just makes sure they always come back in the same predictable order (lowest
id first) instead of in some random order.

```python
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _get_project_or_404(db, project_id)
```

Runs on `GET /projects/5` (or whatever number). The `{project_id}` part in
the address is a placeholder FastAPI fills in automatically and converts to
a real number for us (if you typed letters instead of a number, FastAPI
would reject the request automatically, before our code even runs).

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

Runs on `PUT /projects/5` — "replace this project's data." It finds the
existing row, then for every field in the incoming payload, overwrites that
field on the object (`setattr` is just Python's way of saying "set this
attribute to this value" when the attribute name is a variable, not
hardcoded text). SQLAlchemy quietly notices the object changed and, on
`commit()`, writes the correct `UPDATE` SQL for us — we never touch SQL
directly.

```python
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
```

Runs on `DELETE /projects/5`. `status_code=204` means "success, and there's
deliberately nothing to send back" (there's no `return` line — an empty
response is the correct response for a delete).

### `backend/main.py` — "the front door of the app"

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

- **`from backend.models import project  # noqa: F401`** — this looks
  pointless (we never use anything from it directly in this file) but it's
  actually critical: just *importing* that file is what runs
  `class Project(Base): ...`, which is what registers the `projects` table
  onto `Base`. Skip this import, and `Base` wouldn't know the `projects`
  table should exist at all. The `# noqa: F401` comment tells code-quality
  tools "yes, I know this looks like an unused import, that's intentional,
  don't warn me about it."
- **`Base.metadata.create_all(bind=engine)`** — "look at every table that's
  been registered on `Base`, and create any of them in Postgres that don't
  already exist." This runs once, the moment the app starts.
- **`app = FastAPI(...)`** — creates the actual application object.
- **`app.include_router(projects_router)`** — plugs in all the `/projects`
  addresses we defined earlier.
- **`GET /health`** — the simplest possible "are you alive?" check. It
  deliberately doesn't touch the database — it just proves the web server
  process itself is up and responding.

### `demo/demo_phase1.py` — "proof it all actually works"

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

- **`sys.argv[1]`** — when you run `python3 demo/demo_phase1.py http://localhost:8010`,
  everything after the script name is stored in a list called `sys.argv`.
  `sys.argv[1]` grabs the first extra word you typed — the URL — so the demo
  can point at whatever address the server is actually running on.
- **`show(...)`** — just prints out, in a readable way, exactly what request
  was sent and what came back, so a human can visually check each step
  instead of trusting the script blindly.

```python
def main():
    health = requests.get(f"{BASE_URL}/health"); show(...); health.raise_for_status()
    created = requests.post(f"{BASE_URL}/projects", json={...}); show(...); created.raise_for_status()
    project_id = created.json()["id"]
    ... # list, get, update, delete
    confirm_404 = requests.get(f"{BASE_URL}/projects/{project_id}")
    assert confirm_404.status_code == 404, "Expected 404 after delete"
```

- **`requests.get/post/put/delete(...)`** — the `requests` library is just a
  tool for sending web requests from Python, same as a browser or `curl`
  would.
- **`.raise_for_status()`** — "if this response was an error (4xx/5xx), stop
  everything right now and crash loudly." That way if something's actually
  broken, we find out immediately with a clear error, instead of the script
  quietly limping along with garbage data.
- **`assert confirm_404.status_code == 404, "..."`** — this is the one place
  we *expect* an error response — after deleting, asking for the same
  project again should fail with 404, proving the delete really worked. If it
  doesn't, `assert` crashes the script with the message we gave it.

### The other files, quickly

- **`requirements.txt`** — a shopping list of exact Python package versions
  this project depends on (like `fastapi==0.115.6`). Pinning exact versions
  means "it works on my machine" also means "it works on your machine" —
  nobody accidentally gets a newer, possibly-different version.
- **`.env.example`** — a template file showing what settings (`DATABASE_URL`)
  the app expects, without containing any real secret values. You copy it to
  a real `.env` file and fill in the truth.
- **`docker-compose.yml`** — a recipe file for Docker (a tool that runs
  software in isolated little boxes called *containers*). This one describes
  "run Postgres version 16, remember its data even if the container
  restarts, and know how to check if it's ready." We ended up not using this
  path this time (see below) but it's kept as an alternative for anyone else
  who does want Docker.

---

## 3. The commands we actually ran, and why (including the detours)

### Getting Postgres running — we chose "install it directly" over Docker

```bash
brew install postgresql@16
```
`brew` is Homebrew, a package manager for macOS (a tool that installs
programs from the terminal instead of downloading installers by hand). This
installs Postgres version 16 itself, plus its helper command-line tools
(`psql` to talk to it directly, `createdb` to make new databases, etc).

```bash
brew services start postgresql@16
```
This tells macOS "run Postgres in the background, all the time, and start
it automatically whenever I log in" — like flipping a permanent light switch
on, instead of having to manually start Postgres every single time.

```bash
createdb memoryrag
```
Installing Postgres gives you the *engine*, but not a database for our app
specifically. This one command creates an empty database literally named
`memoryrag` for our app to use.

**A quirk worth understanding:** Homebrew's Postgres, by default, trusts your
Mac's own login user completely for local connections — no password needed.
So the working address for local Homebrew Postgres is
`postgresql+psycopg2://bhavya@localhost:5432/memoryrag` (just your username,
no password). If you instead used the Docker path, `docker-compose.yml`
creates a *different* user (`postgres`, password `postgres`), because we
told it to. Same app code works with either — you just need the right
address in `DATABASE_URL` for whichever Postgres you're actually running.

### Setting up Python — conda, and a legal-agreement speed bump

```bash
conda create -y -n memoryrag python=3.12
```
`conda` is a tool for managing isolated Python installations (an
**environment**) — like giving this one project its own private toolbox of
Python packages, so it can never clash with some other project's toolbox.
This creates a new one named `memoryrag`, with Python version 3.12 inside it.

This actually failed the first time, with an error about Anaconda's "Terms
of Service." Conda now requires you to explicitly agree to some legal terms
before it'll download packages from its default sources. Since agreeing to
legal terms is your call, not something to just click through automatically
for you, I asked first. You chose to accept them:

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

After that, the environment creation worked.

```bash
conda activate memoryrag
pip install -r requirements.txt
```
`conda activate memoryrag` "steps into" that private toolbox — from now on
in that terminal, `python` and `pip` refer to the ones inside `memoryrag`,
not your computer's system-wide Python. `pip install -r requirements.txt`
then installs every package from our shopping list into that toolbox.

### A sneaky bug: `python` didn't mean what we thought

Running `python demo_phase1.py` failed with
`ModuleNotFoundError: No module named 'requests'` — even though we'd *just*
installed `requests`. The reason: on this Mac, the word `python` is
**aliased** (a shortcut set up in the shell) straight to
`/usr/local/bin/python3`, a totally different Python install, completely
ignoring whatever conda environment was active. Typing `python3` instead
worked correctly, because that name wasn't hijacked by the alias and went
through the normal lookup, landing on the conda environment's own Python.

**Lesson:** if a package is "definitely installed" but Python still can't
find it, run `python3 -c "import sys; print(sys.executable)"` (which prints
exactly which Python program you're actually running) to check you're really
using the Python you think you are.

### Starting the server — and a second unrelated surprise

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
`uvicorn` is the program that actually runs a FastAPI app and listens for
web requests. `backend.main:app` tells it exactly where to find our app
object — "look inside the `backend` package, in the `main` module, for
something named `app`."

This failed with "address already in use" — something *else* on this Mac was
already using port 8000 (each running program listening for network
connections needs to claim a unique "port number," like a numbered mailbox;
two programs can't share the same one). Rather than shut down a process we
didn't start (it might have been something you were actively using), we just
told our server to use a different, free mailbox number instead:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8010
```

### Checking it actually works

```bash
curl -s http://localhost:8010/health
python3 demo/demo_phase1.py http://localhost:8010
```
`curl` sends one single web request from the terminal — a fast manual sanity
check. The demo script is the real proof — it's worth re-running any time
you change the `Project` model or its endpoints, as a fast way to catch
anything you broke, before moving on to the next phase.

---

## 4. The big ideas to remember from this phase

- **A database model and an API schema are not the same thing**, even when
  they look almost identical — one is "what's saved," the other is "what's
  allowed to travel over the internet."
- **Dependency injection (`Depends`)** is how FastAPI hands your function
  ready-made things (like a database session) and cleans them up afterward,
  without you writing that setup/teardown code yourself every time.
- **The session lifecycle**: `add` (remember this) → `commit` (actually save
  it) → `refresh` (pull back anything the database generated, like an id).
- **Standard status codes**: `201` = created, `200` = normal success,
  `204` = success with nothing to send back, `404` = doesn't exist.
- **`create_all()` is a starting-out shortcut, not a forever solution** — it
  can add brand-new tables, but it will never safely change an *existing*
  table's columns once real data is sitting in it. A future phase will
  likely introduce a proper "migration" tool (like Alembic) for that.
