# Phase 2 — Multi-User Auth with JWT (Beginner Notes)

## What are we even building in this phase?

Phase 1 gave us a backend that anyone could talk to — there was no concept
of "who are you?" Phase 2 fixes that. We're adding:

1. A **User** table — so the app actually knows different people exist,
   each with their own login (email + password).
2. **Login with tokens** — instead of sending your password on every single
   request (which would be exhausting and unsafe), you log in *once*, get
   handed a special signed piece of text called a **token**, and then show
   that token on every future request as proof "yes, it's still me."
3. A **Chat** table — a chat belongs to *one* project and *one* user, so we
   can prove the whole "who owns what" idea actually works end to end.
4. **Locking the doors** — the existing Project endpoints, and the new Chat
   endpoints, now refuse to answer unless you show a valid token first.

The technical name for "log in once, get a token, use the token everywhere
else" is **JWT authentication** (JWT = JSON Web Token — we'll unpack exactly
what that means below).

We proved it works with a new script, `demo/demo_phase2.py`, which registers
a throwaway user, logs in, creates a project, creates a chat under it, lists
the chats, and — importantly — tries to hit a protected endpoint with *no*
token at all and checks that it's correctly refused.

---

## 1. New words used in this phase

- **Authentication** — proving *who you are* (e.g. "I am the owner of this
  email address, here's my password to prove it").
- **Authorization** — once we know who you are, deciding *what you're
  allowed to do*. Phase 2 only really does authentication; authorization
  here is as simple as "if you're logged in, you can use the app."
- **Hashing** — turning a password into a scrambled, one-way version of
  itself that can be checked but never un-scrambled back into the original.
  We never, ever store someone's actual password — only its hash.
- **JWT (JSON Web Token)** — a compact piece of text the server hands you
  after login. It secretly contains information (like "this is user #4")
  and is *signed*, meaning the server can always verify it wasn't tampered
  with, without needing to look anything up in a database every time.
- **Bearer token** — the standard way of *presenting* a token: you put it in
  a request header that literally looks like `Authorization: Bearer
  <the-token-text>`. "Bearer" just means "whoever is holding (bearing) this
  token is treated as authenticated" — like a movie ticket, not a
  name-checked ID card.
- **Dependency (in FastAPI)** — code that runs automatically *before* your
  actual endpoint, and hands it a ready-to-use result. We already used this
  in Phase 1 for database sessions (`Depends(get_db)`); now we use the same
  trick for "who's making this request?" (`Depends(get_current_user)`).
- **401 Unauthorized** — the standard web status code for "you didn't prove
  who you are (or your proof is invalid/expired)."
- **403 Forbidden** — a *different* status code meaning "I know who you are,
  but you're still not allowed to do this." We'll see below why this
  distinction actually caused us a real bug.

---

## 2. The folder structure now

```
MemoryRag/
├── backend/
│   ├── main.py                  # now wires up auth + chats too
│   ├── schemas.py               # now also has User/Token/Chat shapes
│   ├── dependencies.py          # NEW — the "who is making this request?" check
│   ├── api/
│   │   ├── projects.py          # existing routes, now require login
│   │   ├── auth.py              # NEW — /auth/register and /auth/login
│   │   └── chats.py             # NEW — chat routes, scoped to project + user
│   ├── database/
│   │   └── session.py           # unchanged
│   ├── models/
│   │   ├── project.py           # unchanged
│   │   ├── user.py              # NEW — the "users" table
│   │   └── chat.py              # NEW — the "chats" table
│   └── utils/
│       └── security.py          # NEW — password hashing + JWT creation/checking
├── demo/
│   ├── demo_phase1.py
│   └── demo_phase2.py           # NEW — proves auth + chats work end to end
└── requirements.txt              # a few new packages
```

Notice `dependencies.py` and `utils/security.py` sit *outside* any single
router. That's on purpose: both `auth.py`, `projects.py`, and `chats.py` all
need to check "is this person logged in?", so that logic lives in one shared
place instead of being copy-pasted into three files.

---

## 3. Going file by file

### `backend/models/user.py` — "what does a User look like in the database?"

```python
from sqlalchemy import Column, DateTime, Integer, String, func
from backend.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

This looks almost exactly like `Project` from Phase 1 (see
[phases/phase1.md](phase1.md) for what `Column`, `index`, and
`server_default` mean if you need a refresher). Two things are new here:

- **`unique=True`** on `email` — tells Postgres "refuse to save a second row
  with the same email, no matter what." This is our safety net against two
  accounts sharing one email address, enforced by the database itself, not
  just our Python code.
- **`hashed_password`**, not `password` — we are being very deliberate about
  naming here. This column *never* holds someone's real password, only the
  scrambled hash of it (explained in `security.py` below). Naming it
  `hashed_password` instead of just `password` is a small habit that makes
  it much harder to accidentally leak or log a real password by mistake.

### `backend/models/chat.py` — "what does a Chat look like in the database?"

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from backend.database.session import Base

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

The new idea here is **`ForeignKey`**. `project_id = Column(Integer,
ForeignKey("projects.id"), ...)` means: "this number must match the `id` of
an actual row that already exists in the `projects` table." Think of it like
writing someone's passport number on a form — it's not just *any* number,
it has to correspond to a real passport. This is how a Chat "belongs to" a
specific Project, and `user_id` similarly means it "belongs to" a specific
User. Postgres will actually reject an attempt to save a Chat pointing at a
`project_id` that doesn't exist — another safety net enforced at the
database level, not just in our Python code.

### `backend/utils/security.py` — "hashing passwords and making/checking tokens"

```python
import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

- **`SECRET_KEY`** — this is the single most important secret in the whole
  app. It's the "signature ink" used to sign every token we hand out. If
  someone else got hold of this value, they could forge tokens and pretend
  to be any user. That's exactly why it comes from an environment variable
  (never hardcoded, never committed to git) — same pattern as `DATABASE_URL`
  in Phase 1.
- **`ALGORITHM = "HS256"`** — the specific mathematical recipe used to sign
  and verify tokens. You don't need to understand the math — just know
  "both signing and checking a token must use the exact same algorithm, or
  it'll be rejected."
- **`pwd_context = CryptContext(schemes=["bcrypt"], ...)`** — sets up
  `passlib` (a password-hashing library) to use `bcrypt`, a well-tested
  hashing recipe specifically designed to be *slow* on purpose. That sounds
  backwards, but it's intentional: slow hashing makes it impractically
  expensive for an attacker to guess millions of passwords per second even
  if they somehow stole our whole `users` table.

```python
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)
```

- **`hash_password`** — runs at registration time. Turns `"MyPassword123"`
  into something like `"$2b$12$KIX...long scrambled text..."`. This is what
  actually gets saved to the database — never the original text.
- **`verify_password`** — runs at login time. You *cannot* un-hash a hash
  back into the original password (that's the whole point), so instead we
  hash the password the person just typed in and check if the two hashes
  match. Matching hashes means matching original passwords, without either
  side ever storing or comparing the real password directly.

```python
def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

- **`subject`** — here, this is the user's `id`, turned into text. Inside a
  JWT, the "who is this token for" field is called `sub` (short for
  *subject*) by convention.
- **`"exp": expire`** — every token carries its own expiry time baked right
  into it. After `ACCESS_TOKEN_EXPIRE_MINUTES` minutes, the token becomes
  worthless automatically — even if nobody explicitly "logs it out," it just
  stops being accepted. This limits the damage if a token ever leaks.
- **`jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)`** — takes that
  small dictionary of info and the secret key, and produces the actual token
  string. Anyone can *read* what's inside a JWT (it's not encrypted, just
  encoded — don't put real secrets inside the payload!), but only someone
  who knows `SECRET_KEY` can produce a token that will pass verification.

```python
def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
```

- **`jwt.decode(...)`** — takes a token string, checks the signature matches
  (proving it was really issued by us and hasn't been altered), checks it
  hasn't expired, and gives back the original payload dictionary
  (`{"sub": "4", "exp": ...}`). If *anything* about the token is wrong —
  tampered, expired, garbage text — this raises `JWTError`, which we catch
  and turn into our own `ValueError` so the rest of the app doesn't need to
  know anything about the `jose` library's specific exception types.

### `backend/dependencies.py` — "who is making this request?"

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.user import User
from backend.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)
```

- **`HTTPBearer`** — a ready-made FastAPI tool that knows how to read the
  `Authorization: Bearer <token>` header out of an incoming request, so we
  don't have to parse that text ourselves.
- **`auto_error=False`** — this one line fixed a real bug we hit while
  testing (full story below). By default, `HTTPBearer` would immediately
  reject a request with *no* `Authorization` header at all using a `403`
  status code. We want *every* kind of "not properly logged in" situation —
  missing header, garbage token, expired token — to consistently come back
  as `401`. Setting `auto_error=False` tells it "don't decide anything
  yourself, just hand me `None` if there's no header, and let *my* code
  decide what error to send."

```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

This is the single function that every protected endpoint now depends on.
Step by step, it: checks a token was even sent → tries to decode/verify it →
pulls the user id back out of it → looks that user up in the database → and
if literally any of those steps fails, it stops everything with a `401`
before our actual endpoint code ever runs. If every step succeeds, it hands
back the real `User` object, so our endpoint code can use things like
`current_user.id` without having to redo any of this checking itself.

### `backend/api/auth.py` — "register and log in"

```python
@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

Runs on `POST /auth/register`. Checks nobody's already using that email,
then saves a new user — but notice we never save `payload.password` itself,
only `hash_password(payload.password)`. The response uses `UserOut` (see
`schemas.py` below), which deliberately has no `password` or
`hashed_password` field at all — so even by accident, we could never leak
either the real or hashed password back to the client.

```python
@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)
```

Runs on `POST /auth/login`. Notice the error message is deliberately vague
— `"Incorrect email or password"` — whether the email doesn't exist at all,
*or* the password was wrong for a real account, we say the exact same
thing. This is a small but real security habit: if we said "no account with
that email" vs "wrong password" as two different messages, an attacker could
use that difference to figure out which emails are actually registered,
one guess at a time.

### `backend/api/chats.py` — "chats, scoped to a project and to you"

The shape of this file mirrors `projects.py` from Phase 1 closely (same
`_get_..._or_404` helper pattern), with two new ideas layered on:

```python
router = APIRouter(prefix="/projects/{project_id}/chats", tags=["chats"])
```

The router's address now includes `{project_id}` right in the *prefix*
itself. That means every single chat endpoint automatically requires you to
say which project you're talking about — `POST /projects/4/chats`, `GET
/projects/4/chats`, and so on. There's no way to ask for "a chat" without
also saying which project it lives under.

```python
def _get_chat_or_404(db: Session, project_id: int, chat_id: int, user_id: int) -> Chat:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.project_id == project_id, Chat.user_id == user_id)
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
```

This is the important line for "multi-user" actually meaning something:
notice the filter checks **three** things at once — the chat's `id`
*and* its `project_id` *and* its `user_id`. If another user tries to fetch
your chat by guessing its id, the `user_id` part of this filter simply won't
match their own id, so the query finds nothing and they get a `404`
("doesn't exist") — not a `403` ("exists, but you can't see it"). This is a
deliberate, common security pattern: we'd rather someone not even know a
chat with that id exists than confirm "yes it's there, you're just not
allowed to look."

```python
@router.post("", response_model=ChatOut, status_code=201)
def create_chat(
    project_id: int,
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(db, project_id)
    chat = Chat(project_id=project_id, user_id=current_user.id, title=payload.title)
    ...
```

Notice `current_user.id` — the person creating the chat never gets to *say*
whose chat this is (there's no `user_id` field in `ChatCreate` at all,
deliberately — same trick as Phase 1's `ProjectCreate` not accepting an
`id`). The `user_id` is always taken from `current_user`, which itself only
exists because `get_current_user` already verified the token. There's no
way to create a chat "as" somebody else.

### `backend/api/projects.py` — now requires login too

The only change here is adding `current_user: User = Depends(get_current_user)`
as a parameter to every single endpoint (`create_project`, `list_projects`,
`get_project`, `update_project`, `delete_project`). We don't actually *use*
`current_user` for anything inside those functions — we don't scope projects
per-user in this phase — but simply having it as a dependency is enough:
FastAPI runs `get_current_user` (and therefore the whole "is this a valid
token?" check) *before* the endpoint's own code, and stops with a `401` if
it fails. This is the smallest possible change that turns "anyone can use
this" into "only logged-in people can use this."

### `backend/schemas.py` — new shapes added

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- **`EmailStr`** — instead of a plain `str`, this is a special type from
  Pydantic that automatically checks the text actually *looks* like a valid
  email address (has an `@`, a domain, etc.) before our code ever runs.
  Garbage input gets rejected automatically, the same way Phase 1's
  `ProjectCreate` automatically rejected a missing `name`.
- Same pattern as Phase 1's `ProjectCreate`/`ProjectOut` split: `UserCreate`
  is "what you're allowed to send us," `UserOut` is "what we send back" —
  and `UserOut` has no password field of any kind, on purpose.
- **`Token`** — the shape of what `/auth/login` responds with.
  `token_type: str = "bearer"` always defaults to the word `"bearer"`,
  telling the client exactly how to use this token (put it in an
  `Authorization: Bearer <token>` header).

### `backend/main.py` — wiring the new pieces in

```python
from backend.api.auth import router as auth_router
from backend.api.chats import router as chats_router
from backend.models import chat, project, user  # noqa: F401

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(chats_router)
```

Same pattern as Phase 1: importing `backend.models.user` and
`backend.models.chat` (even though we never use them by name in this file)
is what registers the `users` and `chats` tables onto `Base`, so
`Base.metadata.create_all(bind=engine)` knows to create them too.

---

## 4. A real bug we hit while testing: 403 vs 401

While running the new demo script, the very last check — "confirm an
unauthenticated request gets refused" — failed. It expected a `401` but
actually got back a `403 Forbidden`.

The cause: FastAPI's `HTTPBearer` tool, by default, immediately rejects a
request with *no* `Authorization` header at all, using `403`, before our own
`get_current_user` code even gets a chance to run. But *invalid or expired*
tokens (once our own code checks them) were already correctly returning
`401`. So depending on *how* you failed to authenticate — no header at all,
vs. a bad header — you'd get two different, inconsistent status codes.

The fix was the `auto_error=False` line explained above in
`dependencies.py`: it tells `HTTPBearer` "don't reject anything yourself,
just hand me `None` if nothing was sent," and then our own code explicitly
raises a `401` for that case too — so now *every* flavor of "you're not
properly logged in" consistently comes back as the same status code, `401`.

**Lesson:** third-party tools often have their own default opinions baked
in (here, "no credentials" = 403 by default). When your own app has a
specific, consistent contract in mind (here: "auth failures are always
401"), you sometimes need to explicitly turn off a library's automatic
behavior and take that one decision back into your own hands.

---

## 5. New packages, and a version-pinning gotcha we avoided up front

```
passlib==1.7.4
bcrypt==4.0.1
python-jose[cryptography]==3.3.0
email-validator==2.2.0
```

- **`passlib`** — the password-hashing library.
- **`bcrypt`** — the actual hashing algorithm `passlib` uses underneath.
  We deliberately pinned this to `4.0.1` rather than letting pip grab the
  newest version. Newer `bcrypt` releases removed an internal detail that
  `passlib` 1.7.4 still expects to be there, which causes a confusing crash
  the moment you try to hash a password — even though both packages
  "should" work together. Pinning `bcrypt` to a version known to still have
  that detail sidesteps the whole problem before it ever happens to you.
- **`python-jose[cryptography]`** — creates and verifies JWTs. The
  `[cryptography]` part installs an extra package it needs for the
  signing math.
- **`email-validator`** — what actually powers Pydantic's `EmailStr` check
  mentioned above; without it installed, using `EmailStr` in a schema would
  itself raise an error at startup.

---

## 6. Environment variables — one new one, `SECRET_KEY`

```
DATABASE_URL=postgresql+psycopg2://bhavya@localhost:5432/memoryrag
SECRET_KEY=dev-secret-please-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Same rule as Phase 1's `DATABASE_URL`: never hardcode this in the code,
never commit a real one to git (`.env` is already in `.gitignore`).
`.env.example` shows the *shape* of what's needed without any real secret
value in it, so anyone setting up the project knows exactly what to fill in
for themselves.

---

## 7. Verifying it actually works — the commands we ran

```bash
export DATABASE_URL="postgresql+psycopg2://bhavya@localhost:5432/memoryrag"
export SECRET_KEY="dev-secret-please-change-me"
uvicorn backend.main:app --port 8020
```

Same idea as Phase 1 — start the server, pointing it at real environment
variables instead of hardcoded values. Because `main.py`'s
`Base.metadata.create_all(bind=engine)` runs on startup, the new `users` and
`chats` tables get created automatically the moment the server starts, right
alongside the existing `projects` table — no manual `CREATE TABLE` needed.

```bash
python3 demo/demo_phase2.py http://localhost:8020
```

This walked through, and printed, every step: register → log in → create a
project (now requiring the token) → create a chat under that project →
list chats → and finally, a request to `/projects` with *no* token at all,
confirming it correctly comes back `401`.

We also manually double-checked a few extra edge cases with `curl`:
- Registering the *same* email twice → `400 Email already registered`.
- Logging in with the right email but a wrong password → `401 Incorrect
  email or password`.
- Asking for a chat id that doesn't exist under a project → `404 Chat not
  found`.

All of these matched what the code was supposed to do, confirming the whole
auth + multi-user flow genuinely works, not just the happy path.

---

## 8. The big ideas to remember from this phase

- **Never store real passwords — only hashes.** Hashing is one-way on
  purpose; you check a login by hashing the attempt and comparing hashes,
  never by un-hashing anything.
- **A token is "prove it once, present it everywhere after."** Its
  signature (via `SECRET_KEY`) is what makes it trustworthy without a
  database lookup on every single request just to check "is this real?"
- **Dependencies can protect a whole endpoint, even if you never use their
  return value.** Adding `current_user: User = Depends(get_current_user)`
  is enough to require login, whether or not the function body ever
  actually reads `current_user`.
- **Filter by *all* the ownership fields at once** (`id` + `project_id` +
  `user_id` together) when looking something up, rather than checking
  ownership as a separate step afterward — it's simpler and it naturally
  returns "not found" instead of "found, but forbidden" for other people's
  data.
- **Libraries have their own default opinions; know when to override them.**
  `HTTPBearer`'s default 403-on-missing-header behavior is a good example
  of a sensible-sounding default that didn't match what *our* app's
  contract actually needed.
