# 📘 Phase 7 Prompt Versioning, Context Engineering & Evaluation

> A simple learning journal for Phase 7 of MemoryRAG. Written in plain,
> beginner-friendly language meant to be pasted straight into Notion.

## TL;DR what did we actually make?

Three upgrades that make the system **tunable** and for the first time —
**measurable**:

1. **Versioned prompts** the classifier's instructions moved out of the code
   into `.txt` files (`classifier_v1.txt`, `classifier_v2.txt`), picked by an
   env var. Change or compare prompts without touching code.
2. **Real context engineering** instead of chopping context by character
   count, we now count real **tokens** and split a fixed **token budget** across
   the system prompt, conversation history, and retrieved chunks keeping the
   best and dropping the rest.
3. **Evaluation** a script that scores routing with an actual **accuracy
   percentage** over hand-labeled questions, not a gut feeling.

Plus a new endpoint, **`GET /context-trace/{message_id}`**, that shows exactly
what any answer was built from: what was retrieved, what was kept vs. dropped,
and the token breakdown.

We verified it: routing scored **10/10** on the gold set (with v2 being a bit
cleaner than v1), and the token budget correctly dropped the lowest-scored
chunk first when space was tight.

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/prompts/classifier_v1.txt` / `_v2.txt` | The classifier's instructions, as versioned files you can swap |
| `backend/prompts/__init__.py` | Loads a prompt version, chosen by an env var |
| `backend/llm/context.py` | Counts tokens and fits history + chunks into a token budget |
| `backend/llm/graph.py` | Classifier loads a versioned prompt; context step now token-budgeted |
| `backend/api/context_trace.py` | `GET /context-trace/{message_id}` shows what the LLM was given |
| `backend/models/context_trace.py` | The `context_traces` table |
| `demo/eval_phase7.py` | Scores routing accuracy over 10 labeled questions (v1 vs v2) |

For the deep, line-by-line version, see [`phases/phase7.md`](../phases/phase7.md)
this note is the "story and summary" version.

---

## 🧠 New words explained super simply

- **Token** the unit an LLM actually reads (roughly a word-piece).
  "hello world" = 2 tokens. Models are limited by tokens, so *tokens* are the
  real budget, not characters.
- **tiktoken** a library that counts how many tokens some text is.
- **Token budget** a cap on how many tokens the prompt's changing parts may
  use, split across system / history / context.
- **Context engineering** deciding *what* and *how much* goes into the prompt,
  on purpose, instead of dumping everything and hoping.
- **Prompt versioning** keeping named versions of a prompt so you can change,
  compare, and roll back safely.
- **Gold set / evaluation** a list of questions with human-decided correct
  answers, used to measure the system with a number.
- **Routing accuracy** what fraction of the labeled questions went to the
  right memory type.
- **Context trace** the receipt for one answer: what got retrieved, what was
  kept vs. dropped, and the token counts.

---

## 🛠️ The setup story what we ran, and how it went

1. **Moved the classifier prompt into files.** `classifier_v1.txt` is the
   original; `classifier_v2.txt` is the improved one (with the disambiguation
   fix from Phase 6). An env var `CLASSIFIER_PROMPT_VERSION` picks which no
   code change to switch.

2. **Replaced character truncation with token budgeting.** New `context.py`
   counts tokens with `tiktoken` and splits a budget (default 1200 tokens):
   system prompt first, then ~25% for recent conversation history, then the
   rest for retrieved chunks keeping highest-scored chunks and dropping the
   tail when full.

3. **Added `/context-trace/{message_id}`.** Every `/chat` answer now also
   returns a `message_id`; passing it to this endpoint shows the full "receipt"
   for that answer. The trace is stored in a new `context_traces` table (a new
   table, not a new column because our auto-table-creation can't alter
   existing tables, the recurring lesson from Phases 1 & 4).

4. **Wrote the evaluation.** `eval_phase7.py` runs 10 hand-labeled
   question→type pairs through the router and prints accuracy for *both*
   prompt versions, so a prompt change is judged by a number.

5. **Verified live:**
   - Routing accuracy: **10/10 for both v1 and v2**. But v1 was noisier on one
     question (it tagged the Q2-planning question `['conversation','decision']`
     while v2 gave a clean `['conversation']`) so v2 is more *precise* even
     when the score ties. (Classifier results wobble run to run, which is
     exactly why having a repeatable eval beats eyeballing.)
   - Context trace at the normal budget: showed `system=49, history=69,
     context=116` tokens, all history + all 4 chunks kept, nothing dropped.
   - Context trace at a deliberately tiny budget: correctly **dropped the
     lowest-scored chunk first** and kept the total exactly at the cap.

---

## 🧪 How to try it yourself

### The evaluation (no server needed just the LLM key)

```bash
cd ~/Desktop/MemoryRag
conda activate memoryrag
set -a; source .env; set +a
python3 demo/eval_phase7.py
```

You'll see each question, the type it routed to, OK/MISS, and an accuracy
percentage for v1 and v2.

### The context trace (server running)

```bash
# Terminal 1
./run.sh
python3 demo/seed_phase6.py http://localhost:8010   # give it something to retrieve

# Terminal 2 ask something, note the message_id in the response, then:
curl -s -X POST http://localhost:8010/chat -H "Content-Type: application/json" \
     -d '{"project_id":1,"message":"How do we deploy the backend?"}'
# take the "message_id" from that response, then:
curl -s http://localhost:8010/context-trace/<message_id>
```

The trace shows the token breakdown and, for each retrieved chunk, whether it
was `kept` and how many tokens it cost.

### Try switching prompt versions

Set `CLASSIFIER_PROMPT_VERSION=v1` in `.env`, restart, and re-run the eval to
compare or just watch how routing changes.

### Try a tight budget

Set `CONTEXT_TOKEN_BUDGET=60` in `.env`, restart, ask a question with several
relevant chunks, and look at the trace you'll see lower-scored chunks marked
`kept: false`.

---

## ✅ What to remember going forward

- **Tokens are the real budget, not characters.** Counting tokens and dividing
  them across system / history / context is what context engineering means
  concretely.
- **When space is tight, drop the least-relevant chunks first** easy, because
  they're already sorted by score.
- **Prompts are versioned content, not code.** Files + an env selector let you
  tune and roll back safely, and compare versions.
- **Measure instead of vibe-checking.** A gold set and an accuracy number let
  you *prove* a change helped (or didn't) and catch the run-to-run wobble of
  LLM classifiers.
- **Make the system explain itself.** `/context-trace` is the "show your work"
  view priceless for debugging "why did it answer that?"
