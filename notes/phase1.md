# 📘 Phase 1 — FastAPI + PostgreSQL Skeleton

> A simple learning journal for Phase 1 of MemoryRAG. Written in plain,
> beginner-friendly language — meant to be pasted straight into Notion.

## TL;DR — what did we actually make?

A tiny working backend with one "thing" it manages: a **Project** (just a
name + description + when it was made). You can **C**reate, **R**ead,
**U**pdate, and **D**elete Projects over the web (this is called **CRUD**),
and everything really saves into a real Postgres database — nothing is
faked or in-memory.

We proved it works two ways:
1. A script (`demo/demo_phase1.py`) that automatically runs through the
   whole Create → List → Get → Update → Delete → confirm-it's-gone cycle.
2. Clicking through it by hand in FastAPI's auto-generated web page,
   Swagger UI.

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/database/session.py` | How the app talks to Postgres, and hands out one "conversation" (session) per web request |
| `backend/models/project.py` | Describes what a Project row looks like *inside the database* |
| `backend/schemas.py` | Describes what a Project looks like *when sent over the internet as JSON* |
| `backend/api/projects.py` | The actual web addresses (`/projects`, `/projects/5`, ...) and what each one does |
| `backend/main.py` | The starting point — creates the app, plugs in the routes, adds a health check |
| `demo/demo_phase1.py` | A script that tests the whole thing automatically and prints every step |
| `requirements.txt` | The exact list of Python packages this needs |
| `.env.example` | A template for secret settings (like the database address), with no real secrets in it |
| `docker-compose.yml` | An optional recipe to run Postgres inside Docker instead of installing it directly |

For the deep, line-by-line version of every file above, see
[`phases/phase1.md`](../phases/phase1.md) — this note is the "story and
summary" version, that one is the "read every line" version.

---

## 🧠 New words explained super simply

- **CRUD** — Create, Read, Update, Delete. The four basic things you can do
  to a piece of data.
- **API** — a set of web addresses a program can call to ask another
  program to do something (here: create a project, get a project, etc).
- **Database** — a program whose only job is to save data permanently and
  let you search/update it reliably. We used **Postgres**.
- **ORM (Object-Relational Mapping)** — a trick that lets you write a normal
  Python class, and have a library quietly turn it into a real database
  table for you, so you rarely have to write raw SQL by hand.
- **Schema** — a description of "what shape is this data allowed to be."
  We use one shape for what's saved (`Project`) and a *different* shape for
  what's allowed to travel over the internet (`ProjectCreate`,
  `ProjectOut`, ...) — on purpose, as a safety boundary.
- **Session** — one single "conversation" with the database — open it, do
  some work, save it (`commit`), close it.
- **Dependency Injection** — FastAPI automatically handing your function a
  ready-to-use tool (like a database session) and cleaning it up
  afterward, so you don't write that boilerplate yourself every time.
- **Status code** — a 3-digit number every web response includes, saying
  how it went. `200` = ok, `201` = created, `204` = ok but nothing to show,
  `404` = doesn't exist, `422` = "what you sent me doesn't make sense."
- **Environment variable** — a named setting your computer remembers for
  programs to read, kept outside the code (used here for `DATABASE_URL` so
  we never hardcode a password into the source files).
- **Virtual environment / conda environment** — a private, isolated set of
  installed Python packages just for one project, so different projects'
  package versions never collide with each other.

---

## 🛠️ The setup story — what we ran, and every bump along the way

This is the honest, in-order story of getting Phase 1 running for real —
including the parts that didn't work the first time. That's normal, and
worth keeping so future-you remembers *why* things are set up this way.

1. **Docker was offered first, but skipped.** The original plan was
   `docker-compose up -d` to run Postgres in a container. You asked instead
   to install the exact Postgres version directly on the Mac. Both are
   valid — `docker-compose.yml` is still in the project for anyone who wants
   the Docker route later.

2. **Installed Postgres 16 with Homebrew** (`brew install postgresql@16`),
   started it as a background service (`brew services start postgresql@16`),
   and made the actual project database (`createdb memoryrag`).
   - Quirk learned: Homebrew's Postgres trusts your Mac login user with no
     password, so the connection address became
     `postgresql+psycopg2://bhavya@localhost:5432/memoryrag` — different
     from the Docker version, which uses a `postgres`/`postgres`
     username/password because we defined it that way in
     `docker-compose.yml`.

3. **Set up Python using conda** (per your preference) instead of a plain
   `venv`. Tried `conda create -n memoryrag python=3.12` — it failed the
   first time, asking to accept Anaconda's Terms of Service for its default
   package sources. That's a legal-agreement step, so it was worth pausing
   on rather than just clicking through — you chose to accept it
   (`conda tos accept ...`), then the environment created successfully.

4. **Installed the packages**: `conda activate memoryrag`, then
   `pip install -r requirements.txt`.

5. **Hit a confusing bug**: running `python demo_phase1.py` said `requests`
   wasn't installed — even though it clearly was. Turned out `python` (not
   `python3`) was secretly aliased to a totally different Python install on
   this Mac, bypassing the conda environment entirely. Using `python3`
   instead fixed it immediately. **Takeaway: if an installed package
   "isn't found," double check *which* Python is actually running** with
   `python3 -c "import sys; print(sys.executable)"`.

6. **Started the server**: `uvicorn backend.main:app --port 8000` failed
   with "address already in use" — an unrelated program was already
   sitting on port 8000. Instead of shutting down something we didn't
   start, we just used a free port instead: `--port 8010`.

7. **Verified it all worked**: a quick `curl http://localhost:8010/health`,
   then the full `python3 demo/demo_phase1.py http://localhost:8010` run —
   every step (create, list, get, update, delete, confirm-404) printed out
   and passed.

8. **You then moved the demo script** into its own `demo/` folder, and the
   docs (`README.md`, `phases/phase1.md`) were updated to match the new
   path (`demo/demo_phase1.py`).

---

## 🧪 How to try it yourself, two ways

### Way 1 — the demo script (fully automatic)

```bash
# terminal 1 — start the server
export DATABASE_URL="postgresql+psycopg2://<your-mac-username>@localhost:5432/memoryrag"
uvicorn backend.main:app --reload --port 8010

# terminal 2 — run the demo
python3 demo/demo_phase1.py http://localhost:8010
```

You'll see every request and response printed, ending in
"All CRUD operations completed successfully."

### Way 2 — Swagger UI (by hand, in a browser)

With the server running, open **`http://localhost:8010/docs`**. FastAPI
builds this page automatically just from the code we wrote — you didn't
have to design it.

1. Click **`POST /projects`** → **"Try it out"**.
2. Edit the example JSON, e.g.
   ```json
   { "name": "Swagger Test", "description": "trying it live" }
   ```
3. Click **"Execute"** — see the real response below, including the new
   `id` and `created_at` Postgres generated.
4. Copy that `id`, then try **`GET /projects/{project_id}`**,
   **`PUT /projects/{project_id}`**, and **`DELETE /projects/{project_id}`**
   the same way — "Try it out" → fill in the id/body → "Execute."
5. After deleting, try **`GET /projects/{project_id}`** again — you should
   now see a `404`, proving the delete really happened.

Bonus: click the **"Schema"** tab on any endpoint to see the exact shape
FastAPI expects — this is `schemas.py` made visible.

---

## ✅ What to remember going forward

- Database shape and internet (API) shape are kept as *separate* classes on
  purpose — it's a safety boundary, not accidental duplication.
- Every web request gets its own database session, opened and closed
  automatically by FastAPI's dependency injection — you never manage that
  by hand.
- `commit()` is the actual "save" moment; before that, nothing is
  permanent.
- Always double-check *which* Python/pip you're actually using when
  something "should be installed but isn't found."
- `Base.metadata.create_all()` is a nice shortcut for brand-new projects,
  but it can't safely change existing tables once there's real data in
  them — a later phase will likely need a proper migration tool.
