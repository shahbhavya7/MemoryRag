# Phase 7 — Prompt Versioning, Context Engineering & Evaluation (Beginner Notes)

## What are we even building in this phase?

Phase 6 gave us a working routing agent. But two parts of it were still
crude, and we had no way to *measure* whether it was any good:

1. The classifier prompt was **hard-coded** in Python. Changing it meant
   editing code, and there was no way to keep an old version around to
   compare against.
2. The context builder truncated by **raw character count** — a blunt tool,
   since characters aren't the unit an LLM actually reads or is limited by.
3. We judged routing quality by **eyeballing** a few examples ("looks right")
   — a "vibe check," not a number.

Phase 7 fixes all three:

1. **Versioned prompts** — prompt text moves into files (`classifier_v1.txt`,
   `classifier_v2.txt`), picked by an env var. Swap or A/B them without
   touching code.
2. **Real context engineering** — count actual **tokens** (with `tiktoken`)
   and divide a fixed **token budget** across the system prompt, conversation
   history, and retrieved context, keeping the most valuable pieces and
   dropping the rest.
3. **Evaluation** — a script that runs a fixed set of hand-labeled questions
   through the router and reports **routing accuracy** as a percentage.

Plus a new endpoint, `GET /context-trace/{message_id}`, that shows *exactly*
what the LLM was given for any answer — what was retrieved, what was kept vs.
dropped, and the token breakdown. This is the "show your work" tool.

---

## 1. New words used in this phase

- **Token** — the unit an LLM actually reads and is billed/limited by (roughly
  a word-piece). "hello world" is 2 tokens. Models have a fixed token limit,
  so *tokens*, not characters, are the real budget.
- **tiktoken** — a fast tokenizer library. We use it to count how many tokens
  a piece of text will become, so we can budget precisely.
- **Token budget** — a cap on how many tokens the variable parts of the prompt
  may use, divided across categories (system prompt / history / context).
- **Context engineering** — deliberately deciding *what* goes into the prompt
  and *how much* of the budget each part gets, instead of just dumping
  everything in and hoping it fits.
- **Prompt versioning** — keeping named versions of a prompt (v1, v2, …) so you
  can change wording safely, compare them, and roll back.
- **Evaluation / gold set** — a fixed list of inputs with known-correct
  answers (labeled by a human), used to measure a system with a *number*
  instead of a gut feeling.
- **Routing accuracy** — of the labeled questions, the fraction the router
  sent to the correct memory type. Our first real quality metric.
- **Context trace** — a record of exactly what context was assembled for one
  answer: retrieved items, kept vs. dropped, and token counts.

---

## 2. The folder structure now

```
MemoryRag/
├── backend/
│   ├── prompts/                    # NEW — versioned prompt templates
│   │   ├── __init__.py             #   loader + env-var version selection
│   │   ├── classifier_v1.txt       #   the original classifier (pre-fix)
│   │   └── classifier_v2.txt       #   the improved classifier (current default)
│   ├── llm/
│   │   ├── context.py              # NEW — token counting + budget split + trace
│   │   ├── graph.py                # classifier loads a versioned prompt; context_builder now token-budgeted
│   │   └── rag.py                  # SYSTEM_PROMPT_TEXT exposed for token counting
│   ├── api/
│   │   ├── context_trace.py        # NEW — GET /context-trace/{message_id}
│   │   └── chat.py                 # loads history, passes it in, saves the trace, returns message_id
│   ├── models/
│   │   └── context_trace.py        # NEW — context_traces table
│   └── schemas.py                  # +message_id on ChatResponse, +ContextTraceOut
├── demo/
│   └── eval_phase7.py              # NEW — routing-accuracy metric (v1 vs v2)
└── requirements.txt                 # +tiktoken
```

---

## 3. Going file by file

### `backend/prompts/` — versioned prompt templates

The classifier's instructions now live in plain `.txt` files instead of being
buried in Python. `classifier_v1.txt` is the original (simpler) version;
`classifier_v2.txt` is the improved one with the disambiguation rule we added
in Phase 6 (the fix for the WiFi misroute). The loader:

```python
def load_classifier_prompt(version=None):
    return load_prompt(f"classifier_{version or classifier_version()}")

def classifier_version():
    return os.getenv("CLASSIFIER_PROMPT_VERSION", "v2")
```

- **Why files, not code?** Prompts are *content*, not logic. Putting them in
  files means you can edit wording, keep old versions side by side, and switch
  between them with an env var — no code change, no redeploy of logic. This is
  the beginning of treating prompts as a tunable, versioned artifact.
- **`CLASSIFIER_PROMPT_VERSION`** selects the active version at runtime
  (default `v2`). The eval script uses this to score *both* versions.

### `backend/llm/context.py` — token counting + budget

```python
_ENCODING = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(_ENCODING.encode(text))
```

- **`cl100k_base`** is OpenAI's tokenizer. Our LLM is a Llama model (via Groq),
  so this is an *approximation* of its exact token counts — but for
  *budgeting* (keeping a consistent limit) an approximation is fine; we're not
  billing anyone. A comment in the file says exactly this so nobody mistakes it
  for precise.

```python
def build_context(system_prompt, reranked, history, total_budget=TOTAL_TOKEN_BUDGET):
    system_tokens = count_tokens(system_prompt)
    remaining = max(0, total_budget - system_tokens)
    history_budget = int(remaining * HISTORY_FRACTION)   # 25% of what's left
    # fit history (newest first), then fit chunks (highest score first) into the rest
    ...
    return context_string, trace
```

The budget logic, in plain terms:
1. The **system prompt** is fixed, so count it first and subtract it.
2. Give **conversation history** a share (25%) of what remains, and fit as many
   recent messages as fit — newest first (recent context matters most).
3. Whatever's left is the **retrieved-context** budget. Walk the chunks in
   score order (best first) and keep each until the budget runs out; everything
   after that is **dropped**.
4. Build the trace: token counts per category, and for every retrieved chunk
   whether it was kept, its token count, score, and a preview.

- **Why drop lowest-scored chunks first?** Because the chunks arrive already
  sorted by relevance (from the re-ranker). Keeping the top of that list and
  dropping the tail means, when we can't fit everything, we sacrifice the
  *least* relevant material — the sensible trade.
- **Why budget history separately from context?** So a long conversation can't
  crowd out the retrieved facts (or vice versa). Splitting the budget guarantees
  each gets a fair, predictable share.

### `backend/llm/graph.py` — two changes

**(a) The classifier loads a versioned prompt** instead of an inline string:
```python
@lru_cache(maxsize=8)
def _classifier_template(version):
    return ChatPromptTemplate.from_messages(
        [("system", load_classifier_prompt(version)), ("human", "{query}")]
    )

def classify_intent(query, version=None):
    version = version or classifier_version()
    chain = _classifier_template(version) | get_llm() | StrOutputParser()
    ...
```
- **`@lru_cache`** means each version's template is built once and reused, not
  re-read from disk on every request.
- **`classify_intent` takes an optional `version`** — the graph uses the
  env-selected default, but the eval script can pass an explicit version to
  score v1 and v2 in the same run.

**(b) `context_builder` now uses the token budget** instead of char truncation:
```python
def context_builder(state):
    context, trace = build_context(
        SYSTEM_PROMPT_TEXT, state.get("reranked", []), state.get("history", [])
    )
    return {"context": context, "context_trace": trace}
```
The node got *simpler* — all the real logic moved into the reusable, testable
`build_context`. It now also emits `context_trace` into the graph state, which
the endpoint persists.

### `backend/api/chat.py` — history in, trace out

```python
recent = db.query(Message).filter(Message.project_id == payload.project_id)\
           .order_by(Message.id.desc()).limit(HISTORY_LIMIT).all()
history = [f"{m.role}: {m.content}" for m in reversed(recent)]

final = run_chat_graph(payload.message, project_id=..., final_top_k=..., history=history)
# ... log user + assistant messages, get assistant_message.id ...
if trace is not None:
    db.add(ContextTrace(message_id=assistant_message.id, trace_json=json.dumps(trace)))
    db.commit()
return ChatResponse(..., message_id=assistant_message.id)
```

- **History is loaded in the endpoint** (which already has a DB session) and
  passed *into* the graph, rather than the graph reaching into the database
  itself — keeping the graph's data-access surface small.
- **The trace is saved keyed to the assistant message id**, and that id is
  returned to the caller — so a client can immediately ask
  `/context-trace/{message_id}` to see how that specific answer was built.

### `backend/models/context_trace.py` + `backend/api/context_trace.py`

A new `context_traces` table (id, message_id, trace_json, created_at) stores
each trace as JSON. Making it a **new table** (rather than a column on
`messages`) matters: `Base.metadata.create_all()` only *creates missing*
tables, it never *alters* an existing one — so a new table is created cleanly on
startup, whereas adding a column to `messages` would have needed a manual
migration (the recurring Phase 1/4 lesson). The endpoint just looks the trace
up by `message_id` and returns it (404 if there isn't one).

### `demo/eval_phase7.py` — the metric

```python
GOLD = [
    ("Why did we choose PostgreSQL over MongoDB?", "decision"),
    ("How do we deploy the backend to production?", "workflow"),
    ("What does the slugify function do?", "code"),
    ("What is the office WiFi network name?", "document"),
    ("What did the team agree about Friday deploys in the retro?", "conversation"),
    ... (10 total, 2 per type) ...
]

def evaluate(version):
    correct = sum(expected in classify_intent(q, version=version) for q, expected in GOLD)
    return correct / len(GOLD)
```

- **`GOLD`** is a hand-labeled *gold set*: a human decided the right memory type
  for each question. That's the yardstick.
- It scores **both v1 and v2** and prints each accuracy, so a prompt change is
  judged by a *number* ("v2 = 100%, v1 = 90%"), not a feeling. This is the
  first time in the project we can say "this change made routing better/worse"
  with evidence.
- It calls `classify_intent` directly (no server, no Pinecone/Postgres writes),
  so it's fast and only needs the LLM key. It doesn't pollute memory.

---

## 4. Live verification — what we actually observed

- **Routing accuracy:** both v1 and v2 scored **10/10** on the gold set this
  run. A subtle but real difference showed up though: on "What was decided
  about the mobile app in the Q2 planning call?", v1 returned
  `['conversation', 'decision']` (correct type present, but noisier) while v2
  returned a clean `['conversation']`. So even when raw accuracy ties, v2 is
  *more precise*. (LLM classifiers vary run to run — that variance is itself a
  good reason to have a repeatable eval rather than trusting one lucky look.)

- **Context trace, default budget (1200):** a deploy question produced a trace
  showing `system=49, history=69, context=116, total=234` tokens, 6/6 history
  messages kept, 4/4 retrieved chunks kept, 0 dropped — well within budget.

- **Context trace, tight budget:** forcing a small budget made the accounting
  drop the **lowest-scored** chunk first while keeping the total exactly at the
  cap — confirming the budget logic both counts correctly and sacrifices the
  least-relevant material first, not random ones.

---

## 5. The new package

```
tiktoken==0.13.0
```

- **`tiktoken`** — the tokenizer used to count tokens for the budget. It was
  already present (pulled in by `langchain-openai` back in Phase 4); Phase 7
  just pins it explicitly because we now depend on it directly. On first use it
  downloads a small encoding file and caches it.

---

## 6. New environment variables

```
CLASSIFIER_PROMPT_VERSION=v2     # which classifier prompt file to use
CONTEXT_TOKEN_BUDGET=1200        # total token budget for the prompt's variable parts
```

Both have sensible defaults in code, so the app runs without setting them — but
exposing them as env vars is the point: you can retune the budget or switch
prompt versions per environment without editing code.

---

## 7. The big ideas to remember from this phase

- **Tokens, not characters, are the real budget.** Counting tokens (tiktoken)
  and dividing a fixed budget across system / history / context is what "context
  engineering" concretely means here.
- **Drop the least-relevant material first.** Because chunks are score-sorted,
  fitting them top-down and cutting the tail sacrifices the weakest context when
  space is tight.
- **Treat prompts as versioned content, not code.** Files + an env selector let
  you change, compare, and roll back wording safely.
- **Measure, don't vibe-check.** A gold set + an accuracy number turns "seems to
  route well" into evidence — and lets you prove a prompt change helped (or
  didn't).
- **Make the system explain itself.** `/context-trace` shows exactly what an
  answer was built from — invaluable for debugging "why did it say that?" and
  for trusting the pipeline.
- **A new table beats altering an old one** when you just need to attach new
  data — it sidesteps `create_all()`'s inability to migrate existing tables.
