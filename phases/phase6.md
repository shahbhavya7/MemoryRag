# Phase 6 LangGraph + Adaptive Memory Routing (Beginner Notes)

## What are we even building in this phase?

This is the heart of MemoryRAG. Every phase so far was a building block; this
phase snaps them together into the thing the whole project is named after:
**Adaptive Memory Routing (AMR)**.

Until now, `/chat` (Phase 4) always searched *one* pile of documents. But
Phase 5 gave us five *separate* memory types (document, code, decision,
workflow, conversation). The obvious question: when a user asks something, how
do we know *which* memory to look in? "Why did we choose Postgres?" should
look in **decision** memory; "How do we deploy?" should look in **workflow**
memory. Searching all five every time would be wasteful and noisy.

Phase 6 builds an **agent** that *decides* which memory type(s) a question
needs, then retrieves only from those. We build it with **LangGraph**, a
library for describing an agent as a **graph** of steps ("nodes") with a
shared state flowing through them.

The eight nodes, in order:

```
receive_query → intent_detection → memory_router → retriever
   → re_ranker → context_builder → llm_response → memory_update
```

The **proof point** of this phase isn't the answer text it's the *routing
decision*. So `demo/demo_phase6.py` asks five questions, each aimed at a
different memory type, and prints which type the router picked for each,
asserting all five route correctly.

---

## 1. New words used in this phase

- **Agent** a program that makes decisions about *how* to answer, not just a
  fixed pipeline. Here, the "decision" is which memory type(s) to consult.
- **LangGraph** a library for building agents as a **graph**: you define
  **nodes** (steps) and **edges** (what runs after what), plus a shared
  **state** object that each node reads from and writes to.
- **Node** one step in the graph (a plain Python function). It receives the
  current state and returns the fields it wants to update.
- **State** a dictionary that flows through the graph. Node 1 fills in some
  fields, node 2 reads those and adds more, and so on down the chain.
- **Intent classification** using an LLM to categorize the query (here, into
  one or more of the five memory types). This is the "adaptive" in Adaptive
  Memory Routing.
- **Routing** turning that classification into a concrete choice of which
  Pinecone namespace(s) to actually search.
- **Re-ranking** when results come from more than one namespace, merging
  them and sorting by relevance score so the best rise to the top.

---

## 2. The folder structure now

```
MemoryRag/
├── backend/
│   ├── llm/
│   │   ├── graph.py               # NEW the 8-node LangGraph routing agent (the core)
│   │   ├── client.py              # (unchanged) builds the LLM client
│   │   └── rag.py                 # (unchanged) the grounded prompt -> LLM -> answer chain
│   ├── api/
│   │   └── chat.py                # REWRITTEN /chat now runs the graph
│   ├── memory_writer.py           # NEW shared "save one memory" logic (used by /memories AND the graph)
│   ├── embeddings/
│   │   └── store.py                # +search_namespace() (reads either chunk or memory metadata)
│   └── schemas.py                 # ChatResponse now exposes the routed memory_types
├── demo/
│   └── demo_phase6.py              # NEW proves each question routes to the right memory type
└── requirements.txt                 # +langgraph
```

---

## 3. Going file by file

### `backend/llm/graph.py` the routing agent (the whole point)

**The shared state.** Every node reads and writes this dictionary as it flows
through the graph:

```python
class GraphState(TypedDict, total=False):
    query: str
    project_id: int | None
    final_top_k: int
    intent: list[str]          # memory types the classifier chose
    namespaces: list[str]      # the Pinecone namespaces those map to
    retrieved: list[dict]      # raw hits from all selected namespaces
    reranked: list[dict]       # merged + score-sorted + trimmed
    context: str               # the truncated context string
    answer: str
    memory_update_result: dict # what (if anything) got saved back
```

`total=False` just means "not every field has to be present at once" early
nodes fill in early fields, later nodes fill in later ones.

**The eight nodes**, each a small function taking the state and returning the
fields it updates:

1. **`receive_query`** normalizes the input (strips whitespace, sets the
   default result count). A tidy entry point; a real system might also enforce
   length limits or strip sensitive data here.

2. **`intent_detection`** the "adaptive" step. It calls the LLM with a strict
   classifier prompt that describes each of the five types and says "return
   only the applicable type name(s), comma-separated." We then parse the reply
   defensively:
   ```python
   picked = [tok for tok in re.split(r"[^a-z]+", raw.lower()) if tok in VALID_TYPES]
   ```
   splitting on anything non-alphabetic and keeping only the words that are
   actual valid type names. This tolerates the model replying "decision",
   "decision, workflow", "`decision`", or even a stray sentence, and still
   extracts the real types. If nothing valid comes back, it falls back to
   `["document"]` (the most general type) so retrieval always has somewhere to
   look.

3. **`memory_router`** the routing step: map each chosen type to its Pinecone
   namespace via the `MEMORY_NAMESPACES` dict from Phase 5.
   ```python
   return {"namespaces": [MEMORY_NAMESPACES[t] for t in state["intent"]]}
   ```
   Small and boring on purpose the *smart* part was the classifier; this just
   translates its decision into concrete namespaces to hit.

4. **`retriever`** embeds the query once, then searches *each* selected
   namespace (only those!), tagging every hit with the type it came from:
   ```python
   for memory_type, namespace in zip(state["intent"], state["namespaces"]):
       for hit in search_namespace(namespace, query_embedding, PER_NAMESPACE_TOP_K):
           hit["memory_type"] = memory_type
           retrieved.append(hit)
   ```

5. **`re_ranker`** if two or more namespaces were hit, their results are
   interleaved. Merge them and sort by score, keep the top few:
   ```python
   ranked = sorted(state["retrieved"], key=lambda r: r["score"], reverse=True)
   return {"reranked": ranked[: state["final_top_k"]]}
   ```
   Sorting by score works *across* namespaces because every memory type uses
   the same embedding model and the same cosine metric so the scores are
   directly comparable.

6. **`context_builder`** glue the top chunks into one context string, with a
   **hard character-limit truncation** (`MAX_CONTEXT_CHARS = 2000`). If adding
   a chunk would blow the budget, it's cut off and we stop. This is a blunt
   instrument on purpose Phase 7 replaces it with smarter compression.

7. **`llm_response`** hand the assembled context and the question to the same
   grounded RAG chain from Phase 4 (`answer_with_context`), which returns the
   final answer (and still says "I don't know" if the context doesn't contain
   the answer).

8. **`memory_update`** the "learning" step. It asks the LLM: *does the user's
   message state a NEW decision/fact worth saving?* The prompt is deliberately
   strict: if the user's message is a **question**, never save only save when
   the message is a **declarative statement** ("We decided to..."). On a yes, it
   writes the fact to the right memory type via the shared `store_memory`
   helper. It's wrapped in a try/except that defaults to *not* saving, so a
   flaky LLM reply can never crash a chat or save garbage.

**Wiring the graph:**
```python
g = StateGraph(GraphState)
g.add_node("receive_query", receive_query)
...
g.set_entry_point("receive_query")
g.add_edge("receive_query", "intent_detection")
...
g.add_edge("memory_update", END)
GRAPH = g.compile()
```
The edges are a straight line here (each node feeds the next). LangGraph shines
when you add *branches* and *loops* later, but a linear pipeline is the right
starting shape, and it already gives us a clean, inspectable structure.

> **A real gotcha we hit:** LangGraph forbids a **node** from having the same
> name as a **state key**. We originally had both a `memory_update` node *and* a
> `memory_update` state field, and `compile()` refused with
> `"'memory_update' is already being used as a state key"`. Fix: keep the node
> named `memory_update` (it's in the brief) and rename the state field to
> `memory_update_result`.

### `backend/api/chat.py` /chat now runs the graph

The endpoint shrank to: run the graph, log the exchange, shape the response.
```python
final = run_chat_graph(payload.message, project_id=payload.project_id, final_top_k=payload.top_k)
answer = final.get("answer", "")
# ... log user + assistant messages ...
return ChatResponse(
    answer=answer,
    memory_types=final.get("intent", []),   # <-- the routing decision, surfaced to the caller
    sources=[...],
    memory_update=final.get("memory_update_result"),
)
```
The important addition is `memory_types` in the response: the caller (and the
demo) can *see* which memory the router chose, which is exactly the thing this
phase is meant to demonstrate.

### `backend/memory_writer.py` one place to save a memory

Both the `POST /memories` endpoint (Phase 5) and the graph's `memory_update`
node need to "save one memory entry" (row in Postgres + vector in Pinecone).
Rather than duplicate that, it now lives in one function, `store_memory(db,
type, content, source_ref)`, and both callers use it. The Phase 5 endpoint was
refactored to call it too so there's a single, tested save path.

### `backend/embeddings/store.py` `search_namespace()`

The graph's retriever needs to read hits from any namespace, but a namespace
can hold two shapes of metadata: document *chunks* (text under `chunk_text`)
and memory *entries* (text under `content`). `search_namespace` normalizes
that:
```python
"text": md.get("content") or md.get("chunk_text") or "",
"source_ref": md.get("source_ref") or md.get("source_filename"),
```
so the retriever doesn't have to care which kind it got back.

---

## 4. Two real issues we hit during live verification

**(a) One misroute, fixed by a better classifier prompt.** On the first run,
4/5 questions routed correctly, but *"What is the office WiFi password
situation?"* routed to **conversation** instead of **document**. The classifier
was reading the casual phrasing as "something discussed." The fix was to sharpen
the classifier prompt with an explicit disambiguation rule: *a plain factual
"what is …" question is `document`, not `conversation`; only pick `conversation`
when the query explicitly refers to a discussion/meeting.* After that, all 5/5
routed correctly. This is a good lesson in how much routing quality lives in
the *prompt*, not the code the "adaptive" part is only as good as the
instructions you give the classifier.

**(b) A transient "I don't know" from eventual consistency.** The `code`
question occasionally came back with no sources and an "I don't know" answer —
even though routing was correct because the freshly-seeded `code` vector
sometimes wasn't queryable yet (Pinecone serverless eventual consistency, the
same behavior seen in Phases 3 and 5). A direct re-query a moment later returned
it fine, confirming the logic was correct. The demo now (i) waits until *all
five* namespaces return their seed before starting, and (ii) retries a chat once
if retrieval transiently comes back empty the same "poll/retry for the real
condition" pattern used in earlier phases, rather than trusting a fixed sleep.

**And a good behavior we confirmed:** across the five *questions*, the
`memory_update` node saved *nothing* (questions aren't new facts), so it didn't
pollute memory while the bonus *declarative* statement ("We decided to adopt
trunk-based development…") was correctly saved to `decision` memory. That's the
node doing exactly the right thing in both directions.

---

## 5. The new package

```
langgraph==0.2.76
```

- **`langgraph`** the graph/agent framework. We pinned `0.2.76` specifically:
  the newest LangGraph (1.x) pulls in `langchain-core` 1.x, which conflicts with
  the `langchain-openai` 0.3.x we standardized on back in Phase 4. Pinning a
  LangGraph from the 0.2 line keeps the whole LangChain stack on compatible
  0.3.x versions. (A dependency-compatibility judgment call worth noting so a
  future upgrade is done deliberately, across the whole stack at once.)

---

## 6. How this replaces Phase 4

Phase 4's `/chat` did fixed single-collection retrieval, scoped to a project.
Phase 6's `/chat` runs the routing graph over the five memory types, retrieving
from whichever the classifier picks (globally memories are shared knowledge,
not per-project). `project_id` is still accepted and used to log the exchange in
`messages`, but retrieval is now driven by *memory type*, not project. The
Phase 4 demo was updated to read the new response shape; its old
project-isolation check no longer applies because retrieval semantics changed on
purpose.

---

## 7. The big ideas to remember from this phase

- **Adaptive Memory Routing = classify the question, then search only the
  relevant memory.** That's the idea the whole project is built around, and it
  lives in two nodes: `intent_detection` (classify) and `memory_router` (map to
  namespaces).
- **An agent as a graph** LangGraph lets you express "steps + shared state" as
  named nodes and edges, which is far easier to read, extend, and debug than one
  long function. Today it's a straight line; branches and loops are natural next
  steps.
- **Routing quality lives in the classifier prompt.** The one misroute we hit
  was fixed by clarifying definitions in the prompt, not by changing code.
- **Re-rank by score to merge across memories** safe here because every type
  shares one embedding model + metric, so scores are comparable.
- **Let the agent learn, but conservatively.** `memory_update` writes back only
  on clear declarative statements and fails safe (never saves on error or on a
  question), so the memory doesn't fill up with noise.
- **The routing decision is the deliverable, so surface and test it** exposing
  `memory_types` in the response and asserting on it is what makes this phase's
  behavior *provable*, not just plausible.
