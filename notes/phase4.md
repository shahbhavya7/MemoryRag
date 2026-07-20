# 📘 Phase 4 Basic RAG Chat

> A simple learning journal for Phase 4 of MemoryRAG. Written in plain,
> beginner-friendly language meant to be pasted straight into Notion.

## TL;DR what did we actually make?

An actual **chatbot that answers from your documents**. Phase 3 could only
*find* relevant chunks; Phase 4 takes those chunks, hands them to an **LLM**
(the AI behind things like ChatGPT), and gets back a real written answer —
built *only* from your documents, not from the AI's imagination.

This retrieve-then-answer pattern is called **RAG (Retrieval-Augmented
Generation)**, and it's the whole point of MemoryRAG.

We proved it with `demo/demo_phase4.py`: uploaded a short made-up document
(the Aurora Tram), asked two questions it *can* answer printing both the
answer AND the exact source chunks used then asked one it *can't*, and the
model correctly said "I don't know based on the available documents" instead
of making something up. That last part is the real proof: it's **grounded**,
not hallucinating.

This is deliberately the simplest RAG: one pile of documents, no "which kind
of memory should I look in?" routing yet (that's coming in Phase 5).

---

## 🗂️ The files, in one sentence each

| File | What it's for, in plain words |
|---|---|
| `backend/llm/client.py` | Builds the LLM connection from env vars works with Groq or OpenRouter |
| `backend/llm/rag.py` | The LangChain "chain": fill a prompt → call the LLM → get the answer text |
| `backend/api/chat.py` | The `POST /chat` endpoint: retrieve → answer → log the exchange |
| `backend/models/message.py` | The `messages` table logs each question and answer |
| `backend/embeddings/store.py` | Tweaked so search can filter to one project's documents |
| `backend/schemas.py` | Now also describes the chat request & response shapes |
| `demo/demo_phase4.py` | Uploads a doc, asks grounded + unanswerable questions, shows sources |

For the deep, line-by-line version of every file above, see
[`phases/phase4.md`](../phases/phase4.md) this note is the "story and
summary" version, that one is the "read every line" version.

---

## 🧠 New words explained super simply

- **RAG (Retrieval-Augmented Generation)** find relevant text first, then
  let an AI write an answer using that text. Best of both: real facts + a
  natural-language answer.
- **LLM (Large Language Model)** the AI that writes the answer. We don't
  run it ourselves; we call a hosted one (Groq / OpenRouter) over the
  internet with an API key.
- **Grounding** forcing the AI to answer *only* from the text we gave it,
  so it can't just make things up.
- **Hallucination** when an AI confidently says something false because
  it's guessing. Grounding is how we prevent it.
- **Prompt** the instructions + context + question we send the AI. Good
  wording here is most of what makes RAG behave.
- **Chain (LangChain)** a wired-together sequence of steps
  (prompt → LLM → get text), connected with a `|` pipe, like joining hoses.
- **Provider** who hosts the AI (Groq, OpenRouter...). We made it a config
  setting so switching is one env-var change, no code edits.

---

## 🛠️ The setup story what we ran, and every bump along the way

1. **Added one new package**, `langchain-openai`, and built a small `llm/`
   folder: `client.py` (connect to the AI) and `rag.py` (the prompt → AI →
   answer chain).

2. **Made the LLM provider swappable.** Both Groq and OpenRouter speak the
   *same* API "language" as OpenAI, so one client works for either we just
   change the web address and key based on the `LLM_PROVIDER` env var.
   Default is Groq (free + fast).

3. **Wrote the grounding prompt.** The key line we give the AI: *"Answer using
   ONLY the context below. If it's not there, say you don't know don't make
   anything up."* That single instruction is what turns a make-it-up AI into
   a disciplined, source-faithful one.

4. **Scoped search to one project.** Added a filter so a chat about project 5
   only ever sees project 5's documents never another project's.

5. **A real security near-miss (again).** A real Groq API key briefly landed
   in `.env.example`, which unlike `.env` *is* tracked by git. Caught and
   replaced with a placeholder before it could be committed. (Same lesson as
   the Pinecone key in Phase 3: `.env.example` is for placeholders only.)

6. **First live run the AI worked, but the request still failed!** The
   answer came back perfectly ("...takes exactly 12 minutes..."), but the
   request errored with a `500`. The failure wasn't the AI at all it was
   the very last step, *saving the message to the database*:
   ```
   ForeignKeyViolation: Key (project_id)=(133359) is not present in table "projects".
   ```
   The `messages` table had a rule ("foreign key") saying project_id must
   match a real project row but `/chat` (like document upload) accepts any
   project id, and the demo used one with no matching project.

7. **The fix.** We dropped that foreign-key rule and made `project_id` on
   messages a plain grouping tag exactly how document upload already treats
   it. This keeps the two endpoints consistent and matches Phase 4's simple
   "point it at any project id" design. (We also had to manually `DROP TABLE
   messages` first, because the auto-create-tables step only *creates
   missing* tables it never *changes* one that already exists. That's the
   same `create_all()` limitation first noted back in Phase 1, finally biting
   for real.)

8. **Re-ran the demo full success.** Both answerable questions got correct,
   source-backed answers; the unanswerable one was politely declined; and all
   6 message rows (3 questions + 3 answers) were logged. We also confirmed
   project scoping: asking an *empty* project the same question returned 0
   sources and an "I don't know" proving one project can't see another's
   docs.

---

## 🧪 How to try it yourself

### Terminal 1 start the server

```bash
./run.sh                 # loads .env (incl. LLM_API_KEY) and starts on port 8010
```
Make sure your `.env` has `LLM_PROVIDER`, `LLM_API_KEY` (and Postgres +
Pinecone from earlier phases) filled in.

### Terminal 2 run the demo

```bash
conda activate memoryrag
python3 demo/demo_phase4.py http://localhost:8010
```

You'll see: a document uploaded → two questions answered *with their source
chunks printed* → one out-of-scope question the model declines. That contrast
is the whole point grounded answers vs. a refusal to invent.

### Or, by hand in Swagger UI (`http://localhost:8010/docs`)

1. **`POST /documents/upload`** → give a `project_id` (any number) and a
   paragraph of made-up facts in `text`.
2. Wait ~10-15 seconds (Pinecone settling, same as Phase 3).
3. **`POST /chat`** → send `{"project_id": <same number>, "message": "your
   question"}`. You'll get back an `answer` plus the `sources` it used.
4. Now ask something your document does NOT cover watch it say it doesn't
   know, instead of guessing.
5. Try `POST /chat` with a *different* project_id and the same question you
   should get "I don't know" and zero sources, proving projects are isolated.

---

## ✅ What to remember going forward

- **RAG = retrieve, then generate.** Phase 3 retrieved; Phase 4 generates the
  answer from what was retrieved.
- **Grounding lives in the prompt.** "Use only this context; say you don't
  know otherwise" is what prevents made-up answers it's wording, not code.
- **Always return the sources.** Showing which chunks an answer came from
  makes it checkable, not just trustable.
- **One OpenAI-compatible client covers many providers** Groq vs.
  OpenRouter is a one-line config change.
- **"The AI answered" is not the same as "it worked."** The model replied
  correctly on the first try, but a database rule two lines later still broke
  the request only live testing caught it.
- **`.env.example` is committed to git never let a real key sit in it,**
  even for a moment. Only `.env` is ignored.
