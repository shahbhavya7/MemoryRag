# 📘 Phase 2 — Multi-User Auth with JWT

> A simple learning journal for Phase 2 of MemoryRAG. Written in plain,
> beginner-friendly language — meant to be pasted straight into Notion.

## TL;DR — what did we actually make?

Phase 1 had no idea *who* was using it — anyone could create/edit/delete
any project. Phase 2 adds real logins:

- A **User** can **register** (email + password) and **log in**.
- Logging in gives back a **token** — a signed piece of text you show on
  every future request instead of your password.
- A **Chat** is a new thing that belongs to one project *and* one user.
- Every Project and Chat endpoint now **requires** a valid token — no
  token, no access.

We proved it works with `demo/demo_phase2.py`: register → log in → create a
project → create a chat under it → list chats → and finally, try hitting a
protected route with **no** token and confirm it's correctly refused
(`401 Unauthorized`).

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/models/user.py` | Describes what a User row looks like in the database (email + hashed password) |
| `backend/models/chat.py` | Describes what a Chat row looks like — linked to one project and one user |
| `backend/utils/security.py` | Hashes/checks passwords, and creates/checks login tokens |
| `backend/dependencies.py` | The "who is making this request?" check every protected route relies on |
| `backend/api/auth.py` | The `/auth/register` and `/auth/login` web addresses |
| `backend/api/chats.py` | The chat web addresses, scoped to one project and the logged-in user |
| `backend/api/projects.py` | Same as Phase 1, now also requires a valid token |
| `backend/schemas.py` | Now also describes User/Token/Chat shapes for the internet |
| `demo/demo_phase2.py` | A script that tests register → login → project → chat → 401-check automatically |

For the deep, line-by-line version of every file above, see
[`phases/phase2.md`](../phases/phase2.md) — this note is the "story and
summary" version, that one is the "read every line" version.

---

## 🧠 New words explained super simply

- **Authentication** — proving who you are (logging in).
- **Authorization** — once we know who you are, deciding what you're allowed
  to do. (This phase keeps it simple: logged in = allowed.)
- **Hashing** — scrambling a password into something that can be *checked*
  but never *un-scrambled* back to the original. We only ever save the
  scrambled version.
- **JWT (JSON Web Token)** — the "ticket" you get after logging in. It's
  signed by the server, so the server can always tell if it's real, without
  looking anything up in a database on every single request.
- **Bearer token** — the standard way of showing your token: a header that
  looks like `Authorization: Bearer <the-token-text>`. Like a movie ticket
  — whoever's holding it gets in, no ID check needed.
- **401 Unauthorized** — "you didn't prove who you are, or your proof is
  bad/expired."
- **403 Forbidden** — a *different* meaning: "I know who you are, you're
  just not allowed to do this." (We hit a real bug because of this
  difference — see below!)
- **Dependency** (FastAPI) — code that runs automatically before your actual
  endpoint and hands it a ready-made result. Phase 1 used this for database
  sessions; Phase 2 uses the same trick for "who's logged in?"

---

## 🛠️ The setup story — what we ran, and every bump along the way

1. **Added the new tables.** `users` (email, hashed password, created_at)
   and `chats` (title, which project it belongs to, which user it belongs
   to, created_at) — same pattern as Phase 1's `projects` table.

2. **Wrote the password/token helpers** in `backend/utils/security.py`,
   using two new libraries: `passlib` (hashing) and `python-jose` (tokens).

3. **Installed the new packages** into the same conda environment from
   Phase 1:
   ```bash
   conda activate memoryrag
   pip install passlib==1.7.4 bcrypt==4.0.1 "python-jose[cryptography]==3.3.0" email-validator==2.2.0
   ```
   - We deliberately pinned `bcrypt` to `4.0.1` instead of letting it
     install the newest version. Newer `bcrypt` releases are known to break
     `passlib`'s version check and crash the first time you try to hash a
     password — pinning an older, compatible version avoids that trap
     entirely before it ever bites us.

4. **Added a new secret setting**, `SECRET_KEY` — this is what signs every
   token. Same rule as `DATABASE_URL` in Phase 1: never hardcode it, never
   commit a real one, keep it in an environment variable.
   ```bash
   export DATABASE_URL="postgresql+psycopg2://bhavya@localhost:5432/memoryrag"
   export SECRET_KEY="dev-secret-please-change-me"
   ```

5. **Wrote the actual routes**: `/auth/register`, `/auth/login`, the chat
   CRUD endpoints under `/projects/{project_id}/chats`, and added the login
   requirement to all the existing `/projects` endpoints.

6. **Started the server and ran the new demo script** — and hit a real bug
   on the very last step.

7. **The 403 vs 401 bug.** The demo's last check — "an unauthenticated
   request should get `401`" — was actually getting `403 Forbidden`
   instead. The reason: FastAPI's built-in `HTTPBearer` tool rejects a
   request with *no* login header at all using `403`, by default, before
   our own code even runs — but *bad/expired* tokens (which our own code
   checks) were correctly returning `401`. Two different error codes for
   basically the same problem ("you're not logged in") isn't a good,
   predictable API. **Fix:** we told `HTTPBearer` not to auto-reject
   anything itself (`HTTPBearer(auto_error=False)`), and instead our own
   `get_current_user` function now raises the `401` itself in every case —
   so the API always responds the same way, no matter *how* exactly you
   failed to prove who you are.

8. **Re-ran the demo — everything passed**, including the now-correct
   `401`. We also spot-checked a few extra cases by hand with `curl`:
   registering the same email twice (→ `400`), logging in with a wrong
   password (→ `401`), and asking for a chat id that doesn't exist (→
   `404`) — all behaved exactly as expected.

---

## 🧪 How to try it yourself

### Terminal 1 — start the server

```bash
conda activate memoryrag
export DATABASE_URL="postgresql+psycopg2://<your-mac-username>@localhost:5432/memoryrag"
export SECRET_KEY="some-long-random-string"
uvicorn backend.main:app --reload --port 8010
```

### Terminal 2 — run the demo

```bash
python3 demo/demo_phase2.py http://localhost:8010
```

You'll see: register → log in → create project → create chat → list chats
→ the final "no token" request correctly refused with `401`, ending in
"All Phase 2 auth + multi-user checks completed successfully."

### Or, by hand in Swagger UI (`http://localhost:8010/docs`)

1. **`POST /auth/register`** → "Try it out" → send an email + password.
2. **`POST /auth/login`** → same email + password → copy the
   `access_token` from the response.
3. Click the green **"Authorize"** lock icon at the top of the page, paste
   just the token (no need to type "Bearer", Swagger adds that for you),
   and click "Authorize." Now every request from Swagger automatically
   includes your token.
4. Try **`POST /projects`**, then **`POST /projects/{project_id}/chats`**,
   then **`GET /projects/{project_id}/chats`** — all should now work.
5. Click "Authorize" again and log out (clear the token), then try
   **`GET /projects`** again — you should see a `401`, proving the lock
   actually works.

---

## ✅ What to remember going forward

- **Never store real passwords.** Only ever save a one-way hash, and check
  logins by comparing hashes, never the original text.
- **A token is "prove it once, present it everywhere after."** Its
  signature is what makes it trustworthy without a database round-trip on
  every request just to ask "is this legit?"
- **A FastAPI dependency can lock a whole endpoint even if its result is
  never used inside the function** — just requiring it is enough to force
  the check to run first.
- **When looking up "my own" data, filter by every ownership field at
  once** (id + project + user together) rather than checking ownership as
  a separate step — it naturally returns "not found" instead of leaking
  "found, but not yours."
- **Watch out for library defaults that quietly conflict with your own
  app's contract** — `HTTPBearer`'s default 403-on-missing-header is a
  perfect example of "reasonable on its own, wrong for what we needed."
