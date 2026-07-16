# Phase 4 — Basic RAG Chat (Beginner Notes)

## What are we even building in this phase?

Phase 3 gave us semantic *search* — ask a question, get back the most
relevant chunks of text. But it stopped there: it handed you raw chunks, not
an actual answer. You still had to read the chunks yourself.

Phase 4 adds the missing final step: after retrieving the relevant chunks,
we hand them to an **LLM** (a large language model, like the ones behind
ChatGPT) along with your question, and ask it to write a real answer *based
only on those chunks*. This pattern — **retrieve relevant text, then let an
LLM answer using it** — is called **RAG: Retrieval-Augmented Generation**.
It's the entire reason MemoryRAG exists.

The magic word is **grounded**. A plain LLM, asked a question, answers from
its own training memory and will happily *make things up* when it doesn't
know (this is called hallucination). A RAG system instead forces the LLM to
answer only from the specific documents *you* gave it — so answers are
traceable back to real sources, and when the documents don't contain the
answer, a well-built RAG system says "I don't know" instead of inventing
something.

This phase is deliberately the *simplest possible* RAG: one collection of
documents, no "which memory type should I use?" routing yet (that's Phase 5
and beyond). Just: question in → relevant chunks out → LLM answer → done.

We proved it with `demo/demo_phase4.py`, which uploads a short made-up
document, asks questions answerable from it (and prints both the answer AND
the exact source chunks, so you can *see* the answer came from the sources),
then asks one question the document can't answer — showing the model
declines rather than hallucinating.

---

## 1. New words used in this phase

- **RAG (Retrieval-Augmented Generation)** — the technique of retrieving
  relevant text first, then having an LLM generate an answer using that
  text. "Augmented" = the LLM's answer is boosted by real retrieved facts,
  instead of relying only on what it happened to memorize during training.
- **LLM (Large Language Model)** — the AI that actually writes the answer
  in natural language. We don't run it ourselves (it's huge); we call a
  hosted one over the internet via an API key.
- **Grounding** — making the LLM answer *only* from provided source text,
  so answers are traceable and it doesn't just make things up.
- **Hallucination** — when an LLM confidently states something false because
  it's guessing from training memory rather than real given facts. Grounding
  is the defense against this.
- **Prompt** — the full set of instructions + context + question we send to
  the LLM. Getting the prompt right is most of what makes RAG work well.
- **Chain (LangChain)** — LangChain's word for a sequence of steps wired
  together: here it's *prompt → LLM → parse the text output*. LangChain lets
  you connect these with a `|` (pipe) operator, like plumbing pipes together.
- **Provider** — the company hosting the LLM we call (Groq, OpenRouter,
  etc.). We made this configurable so you can switch providers by changing
  one env var, without touching code.
- **OpenAI-compatible API** — many LLM providers copy OpenAI's API shape
  exactly, so the same client code works against all of them just by
  changing the web address (base URL) and API key. We rely on this to
  support both Groq and OpenRouter with a single client.

---

## 2. The folder structure now

```
MemoryRag/
├── backend/
│   ├── main.py                    # now also wires up /chat + the messages table
│   ├── schemas.py                 # now also has ChatRequest / ChatResponse shapes
│   ├── api/
│   │   └── chat.py                # NEW — the POST /chat endpoint (retrieve -> answer -> log)
│   ├── llm/
│   │   ├── client.py              # NEW — builds the LLM client from env vars (provider-agnostic)
│   │   └── rag.py                 # NEW — the LangChain prompt -> LLM -> answer chain
│   ├── models/
│   │   └── message.py             # NEW — the "messages" table (logs each exchange)
│   └── embeddings/
│       └── store.py                # tweaked — search() can now filter by project_id
├── demo/
│   └── demo_phase4.py              # NEW — proves grounding is real, not assumed
└── requirements.txt                 # one new package: langchain-openai
```

The new `llm/` folder mirrors the `embeddings/` folder from Phase 3 — a
small package whose only job is "everything about talking to the LLM,"
kept separate from the API layer so the endpoint stays thin and readable.

---

## 3. Going file by file

### `backend/llm/client.py` — "build the right LLM client from env vars"

```python
import os
from langchain_openai import ChatOpenAI

PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-3.3-70b-instruct",
}

def get_llm() -> ChatOpenAI:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider)
    base_url = PROVIDER_BASE_URLS.get(provider)

    if base_url is None:
        raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Supported: ...")
    if not api_key:
        raise ValueError("LLM_API_KEY is not set. Add it to your .env ...")

    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0)
```

- **Why `ChatOpenAI` for a non-OpenAI provider (Groq/OpenRouter)?** — Both
  Groq and OpenRouter expose an API that's *shaped exactly like OpenAI's*.
  So LangChain's OpenAI client works against them unchanged; we just point
  its `base_url` at the right server and give it the right key. This is why
  one small dictionary (`PROVIDER_BASE_URLS`) is all it takes to support
  multiple providers — no separate client library per provider.
- **`os.getenv("LLM_PROVIDER", "groq")`** — reads which provider to use from
  the environment, defaulting to Groq. Same "config comes from env, never
  hardcoded" rule as `DATABASE_URL` and `PINECONE_API_KEY` in earlier phases.
- **`model = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider)`** — lets
  you override the exact model if you want, but falls back to a sensible
  default for whichever provider you picked, so it works out of the box.
- **The two `raise ValueError` checks** — fail *early and clearly* if the
  provider is unknown or the key is missing, with a message telling you
  exactly what to fix, instead of a confusing error deep inside an API call
  later.
- **`temperature=0`** — "temperature" controls how random/creative the LLM
  is. For RAG we want it as low as possible (`0`): we want it to stick
  faithfully to the retrieved facts, not get creative. Creativity here would
  just mean more hallucination.
- **Why a `get_llm()` function instead of building the client once at import
  time?** — Building it lazily (only when called) means simply *importing*
  this file never crashes, even if the key isn't set yet. Contrast with
  Phase 3's Pinecone client, which is built at import — a deliberate
  difference, because a missing LLM key should only matter when you actually
  try to chat, not stop the whole app from starting.

### `backend/llm/rag.py` — "the actual RAG chain: prompt → LLM → answer"

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from backend.llm.client import get_llm

_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant for the MemoryRAG project. "
     "Answer the user's question using ONLY the context below. "
     "If the answer is not in the context, say you don't know based on the "
     "available documents — do not make anything up."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

def answer_with_context(question: str, chunks: list[str]) -> str:
    chain = _PROMPT | get_llm() | StrOutputParser()
    context = "\n\n---\n\n".join(chunks) if chunks else "(no relevant documents found)"
    return chain.invoke({"context": context, "question": question})
```

This tiny file is the heart of the whole phase.

- **The system message is where grounding actually happens.** Those two
  sentences — "use ONLY the context below" and "if it's not there, say you
  don't know, don't make anything up" — are the instructions that turn a
  free-associating LLM into a disciplined, grounded one. This is *prompt
  engineering*: the behavior we want is achieved by carefully wording the
  instructions, not by changing any code logic.
- **`ChatPromptTemplate.from_messages([...])`** — builds a reusable template
  with two parts: a fixed **system** message (the rules, same every time)
  and a **human** message with `{context}` and `{question}` placeholders
  that get filled in per request. Separating a fixed system instruction from
  the per-question content is the standard way to prompt chat models.
- **`chain = _PROMPT | get_llm() | StrOutputParser()`** — this is the
  LangChain "chain," read left to right like a pipeline: take the filled-in
  prompt → send it to the LLM → run the LLM's reply through `StrOutputParser`
  (which just extracts the plain text string out of the LLM's richer
  response object). The `|` operator is LangChain's way of gluing steps into
  one callable thing.
- **`context = "\n\n---\n\n".join(chunks)`** — glues the retrieved chunks
  into one block of text, separated by `---` dividers so the model can tell
  where one chunk ends and the next begins. The `if chunks else "(no
  relevant documents found)"` handles the case where retrieval found nothing
  — we still send *something* sensible rather than an empty context.
- **`chain.invoke({...})`** — actually runs the whole pipeline, filling the
  placeholders and returning the final answer string.

### `backend/models/message.py` — "log every exchange"

```python
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False, index=True)   # NOTE: no ForeignKey — see below
    role = Column(String, nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

Same ORM-model pattern as Phase 1's `Project` and Phase 2's `User`/`Chat`.
Two things worth calling out:

- **`role`** — each row is one message, tagged either `"user"` (what you
  asked) or `"assistant"` (what the LLM answered). So one chat exchange
  becomes two rows. This mirrors how chat APIs represent conversations.
- **`content = Column(Text, ...)`** — we use `Text` here instead of `String`
  because answers can be long; `Text` is the SQL type for arbitrarily long
  text, whereas `String` can imply a length limit.
- **Why `project_id` has NO `ForeignKey` here** (unlike `Chat` in Phase 2) —
  this was a deliberate decision made *during* this phase, prompted by a real
  bug; see section 4 below.

### `backend/embeddings/store.py` — "search, now scoped to a project"

The only change was making retrieval filter by project:

```python
def search(query_embedding, top_k, project_id=None):
    query_filter = {"project_id": project_id} if project_id is not None else None
    result = _get_index().query(
        vector=query_embedding, top_k=top_k, namespace=NAMESPACE,
        include_metadata=True, filter=query_filter,
    )
    ...
```

- **`filter={"project_id": project_id}`** — Pinecone can restrict a search to
  only vectors whose metadata matches. So when the chat asks about project 5,
  it only ever compares against project 5's documents — project 7's docs are
  invisible to it. This is what makes the "chat only sees its own project's
  documents" guarantee real, enforced at the database query level.
- **`project_id=None` default** — keeps the existing `/documents/search`
  endpoint (which doesn't pass a project) working exactly as before. Only the
  new chat path opts into filtering. Adding an optional parameter with a
  safe default is a clean way to extend a function without breaking existing
  callers.

### `backend/api/chat.py` — "the endpoint: retrieve → answer → log"

```python
@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    # 1. Retrieve
    query_embedding = embed_query(payload.message)
    retrieved = search(query_embedding, payload.top_k, project_id=payload.project_id)

    # 2. Generate
    chunk_texts = [r["text"] for r in retrieved]
    answer = answer_with_context(payload.message, chunk_texts)

    # 3. Log both sides of the exchange
    db.add(Message(project_id=payload.project_id, role="user", content=payload.message))
    db.add(Message(project_id=payload.project_id, role="assistant", content=answer))
    db.commit()

    sources = [ChatSource(text=r["text"], score=r["score"],
                          source_filename=r["metadata"]["source_filename"]) for r in retrieved]
    return ChatResponse(answer=answer, sources=sources)
```

The endpoint reads like the three-line story of RAG, and that's on purpose —
all the real work lives in the small helper functions (`embed_query`,
`search`, `answer_with_context`), so this endpoint just *orchestrates* them:

1. **Retrieve** — turn the question into a vector and pull the most similar
   chunks *for this project only*.
2. **Generate** — pass just the chunk texts to the RAG chain to get an
   answer.
3. **Log** — save both the question and the answer to the `messages` table
   (`db.add` twice, then one `db.commit` — same session lifecycle as Phase 1).

- **Returning `sources` alongside `answer`** is a small but important design
  choice: it makes the answer *auditable*. Anyone (including the demo) can
  see exactly which chunks the answer was built from, so grounding is
  verifiable, not just claimed. Real RAG products show these as citations.

### `backend/schemas.py` — the new request/response shapes

```python
class ChatRequest(BaseModel):
    project_id: int
    message: str
    top_k: int = 4

class ChatSource(BaseModel):
    text: str
    score: float
    source_filename: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
```

Same input-shape-vs-output-shape discipline as every earlier phase.
`top_k: int = 4` means "retrieve 4 chunks by default" — enough context to
answer most questions without stuffing the prompt with too much (which costs
more and can dilute the answer). `ChatResponse` bundles the answer together
with its sources so the caller gets both in one response.

---

## 4. A real bug we hit during live verification: the foreign-key clash

When the demo was first run live (with a real Groq key), the LLM answer came
back **perfectly** — but the request still failed with a `500` error. The
traceback showed the failure wasn't in the RAG at all; it was in the very
last step, *logging the message*:

```
psycopg2.errors.ForeignKeyViolation: insert or update on table "messages"
violates foreign key constraint "messages_project_id_fkey"
DETAIL: Key (project_id)=(133359) is not present in table "projects".
```

**What happened:** the `messages` table was first written with a *foreign
key* on `project_id` pointing at the `projects` table — meaning "you can only
log a message for a project that actually exists as a row in `projects`." But
the `/chat` endpoint (like `/documents/upload` before it) accepts *any*
`project_id` as a free-form number, and the demo used a random one that had
no matching `projects` row. So Postgres correctly refused the insert.

**The fix and the reasoning:** there were two ways to resolve this —
(a) force every `/chat` caller to first create a real project (which, since
Phase 2 locked down project creation behind login, would mean the demo has
to register → log in → create a project → *then* chat), or (b) drop the
foreign key and treat `project_id` as a plain logical grouping tag — exactly
how `/documents/upload` already treats it (it stores project_id as vector
metadata with no database check at all).

Option (b) was chosen, because it makes the two endpoints that take a
`project_id` behave *consistently*, and it matches what Phase 4's simple
`{project_id, message}` contract implies — a lightweight chat you can point
at any project id, not a heavyweight flow requiring pre-created, owned
projects. The `messages.project_id` column is now a plain indexed integer
with a clear code comment explaining why.

**A wrinkle worth knowing:** because the `messages` table had *already* been
created in Postgres (with the foreign key) the first time the server started,
just editing the model wasn't enough — `Base.metadata.create_all()` only
ever *creates missing* tables, it never *alters* an existing one. So the
existing empty `messages` table had to be manually dropped (`DROP TABLE
messages;`) so that the next startup would recreate it fresh, without the
foreign key. This is the exact limitation of `create_all()` that was flagged
back in Phase 1's notes — and here it actually bit, a concrete reminder of
why real projects eventually adopt a proper migration tool (like Alembic).

**Lesson:** "the AI answered correctly" and "the request succeeded" are two
different things — the LLM call worked on the very first try, but the feature
was still broken by a database constraint two lines later. Only running it
live surfaced that; reading the code alone, the foreign key looked perfectly
reasonable.

---

## 5. The new package

```
langchain-openai==0.3.35
```

- **`langchain-openai`** — provides both the `ChatOpenAI` client (which, as
  explained, works for any OpenAI-compatible provider, not just OpenAI) and
  pulls in `langchain-core` (which gives us `ChatPromptTemplate`,
  `StrOutputParser`, and the `|` chain operator). One install covers the
  whole LangChain surface this phase needs.

---

## 6. Environment variables — the LLM settings

```
LLM_PROVIDER=groq                 # or: openrouter
LLM_API_KEY=your-real-key
# LLM_MODEL=...                    # optional override
```

Same secret-handling rules as always: real key lives only in `.env` (which is
gitignored); `.env.example` carries only placeholders. (During this phase a
real key briefly landed in `.env.example` and was caught and replaced with a
placeholder before it could be committed — `.env.example` *is* tracked by
git, so it must never hold a real secret.)

---

## 7. The big ideas to remember from this phase

- **RAG = retrieve, then generate.** Search finds the relevant text; the LLM
  turns that text into an actual answer. Phase 3 did the first half; Phase 4
  completes the loop.
- **Grounding is created in the prompt.** The instruction "answer only from
  this context, and say you don't know otherwise" is what stops
  hallucination — it's wording, not code logic.
- **Return your sources.** Sending back the chunks an answer was built from
  makes grounding *verifiable* and answers auditable — the difference between
  "trust me" and "here's my evidence."
- **Scope retrieval to the right subset** (here, per project) at the database
  query level, so a chat can't accidentally answer from data that isn't
  supposed to be visible to it.
- **One OpenAI-compatible client can serve many providers** — swapping Groq
  for OpenRouter is a config change, not a code change.
- **"The model answered" ≠ "the request worked."** End-to-end live testing
  catches failures (like the foreign-key clash) that happen *around* the AI
  call, which code review alone can miss.
- **`create_all()` still can't alter existing tables** — changing a model's
  columns after the table exists means dropping/migrating the table, the same
  limitation first noted in Phase 1, now encountered for real.
