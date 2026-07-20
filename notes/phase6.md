# 📘 Phase 6 LangGraph + Adaptive Memory Routing

> A simple learning journal for Phase 6 of MemoryRAG. Written in plain,
> beginner-friendly language meant to be pasted straight into Notion.

## TL;DR what did we actually make?

**The core of the whole project.** We built an *agent* that, for each
question, figures out **which memory type to look in** decision? workflow?
code? and then searches only that one, instead of everything. That smart
choice is called **Adaptive Memory Routing**.

We built it with **LangGraph**, which lets you describe an agent as a little
flowchart of steps ("nodes") with a shared bag of data flowing through them.
Eight nodes, in a line:

```
receive_query → intent_detection → memory_router → retriever
   → re_ranker → context_builder → llm_response → memory_update
```

`/chat` now runs this graph. Its response includes `memory_types` the
router's choice which is the whole proof point of this phase.

We proved it with `demo/demo_phase6.py`: five questions, each aimed at a
different memory type, and it printed which type the router picked for each —
**5/5 correct**. A bonus step then *stated* a new decision and watched the
`memory_update` node save it into decision memory.

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/llm/graph.py` | The 8-node LangGraph routing agent the heart of this phase |
| `backend/api/chat.py` | `/chat`, rewritten to run the graph and return the routing decision |
| `backend/memory_writer.py` | One shared "save a memory" function, used by `/memories` and the graph |
| `backend/embeddings/store.py` | Added `search_namespace()` so the graph can read any namespace |
| `backend/schemas.py` | `/chat` response now includes `memory_types` (which memory was picked) |
| `demo/demo_phase6.py` | Asks 5 type-specific questions, prints the routing decision for each |

For the deep, line-by-line version, see [`phases/phase6.md`](../phases/phase6.md)
this note is the "story and summary" version.

---

## 🧠 New words explained super simply

- **Agent** a program that *decides how* to answer, not just a fixed
  pipeline. Here it decides which memory type(s) to search.
- **LangGraph** a tool for building an agent as a flowchart: **nodes**
  (steps), **edges** (what comes next), and a shared **state** (a bag of data
  passed along and filled in as it goes).
- **Node** one step, just a Python function that reads the state and returns
  what it wants to change.
- **Intent classification** asking the LLM "which category is this
  question?" the smart bit that makes routing "adaptive."
- **Routing** turning that category into "search *this* namespace."
- **Re-ranking** when answers come from more than one memory, merging them
  and sorting by score so the best come first.

---

## 🛠️ The setup story what we ran, and every bump along the way

1. **Installed LangGraph** but the newest version dragged in a newer
   `langchain-core` that clashed with the `langchain-openai` we've used since
   Phase 4. Fix: pin `langgraph==0.2.76`, which stays on the compatible 0.3.x
   LangChain line. (Lesson: upgrade a whole framework family together, on
   purpose not one piece at a time.)

2. **Built the 8-node graph** in `backend/llm/graph.py`: receive → detect
   intent → route → retrieve → re-rank → build context → answer → maybe save.

3. **Hit a LangGraph rule:** a node can't share a name with a state field. We
   had both a `memory_update` node and a `memory_update` state key, and it
   refused to compile. Fix: renamed the state field to
   `memory_update_result`, kept the node named `memory_update`.

4. **Replaced `/chat`** so it runs the graph and returns the routing decision
   (`memory_types`) alongside the answer and sources.

5. **First live run: 4/5 routed correctly.** The odd one out "What is the
   office WiFi password situation?" routed to *conversation* instead of
   *document*, because the casual wording sounded like "something discussed."
   Fix: sharpened the classifier prompt with a clear rule *a plain factual
   "what is …" question is document, not conversation.* After that: **5/5**.
   (Big lesson: routing quality lives in the *prompt*, not the code.)

6. **A transient "I don't know" on the code question.** Routing was correct,
   but retrieval briefly returned nothing Pinecone's eventual-consistency
   lag on a just-seeded vector (same gremlin as Phases 3 & 5). A direct
   re-query worked fine. Fix: the demo now waits until *all five* namespaces
   are searchable, and retries a chat once if retrieval comes back empty.

7. **Confirmed the `memory_update` node behaves.** Across the 5 *questions* it
   saved nothing (questions aren't new facts → no memory pollution). Then a
   *declarative* statement ("We decided to adopt trunk-based development…") was
   correctly saved into decision memory. Right call in both directions.

8. **Checked the database:** exactly 6 memories (5 seeds + 1 saved decision)
   and 12 messages (6 exchanges) proving the questions didn't spawn junk
   memories.

---

## 🧪 How to try it yourself

### Terminal 1 start the server

```bash
./run.sh            # loads .env (LLM key, Pinecone, Postgres), serves on 8010
```

### Terminal 2 run the routing demo

```bash
conda activate memoryrag
python3 demo/demo_phase6.py http://localhost:8010
```

Watch each question print the memory type the router chose (5/5 should match),
then the bonus step save a stated decision into memory.

### Or, by hand in Swagger UI (`http://localhost:8010/docs`)

1. Seed a few typed memories with **`POST /memories`** (e.g. a `decision`, a
   `workflow`). Wait ~10-15s (Pinecone settling).
2. **`POST /chat`** → `{"project_id": 1, "message": "why did we choose X?"}`.
   Look at `memory_types` in the response that's the router's decision. It
   should say `["decision"]`, and the answer should come from your decision
   entry.
3. Try a workflow-style question ("how do we deploy?") and watch it route to
   `["workflow"]` instead.
4. Now *state* something: `{"message": "We decided to use X because Y."}` and
   check the `memory_update` field of the response it should show the fact
   was saved.

---

## ✅ What to remember going forward

- **Adaptive Memory Routing = classify the question, then search only the
  right memory.** It lives in two nodes: `intent_detection` (classify) and
  `memory_router` (pick the namespace). This is the idea the project is named
  for.
- **An agent as a graph is easier to reason about** than one big function —
  named steps + a shared state you can inspect at each hop.
- **Routing quality is mostly the classifier prompt.** Our one misroute was
  fixed by clarifying definitions, not by changing logic.
- **Re-rank by score to merge across memories** fair because all types share
  one embedding model + metric.
- **Let the agent learn, but carefully.** `memory_update` saves only clear
  new statements and never on a plain question, so memory stays clean.
- **Prove the decision, don't just trust the answer.** Surfacing
  `memory_types` and asserting on it is what makes the routing *verifiable* —
  the real deliverable of this phase.
