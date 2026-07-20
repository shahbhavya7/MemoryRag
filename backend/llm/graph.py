"""The Adaptive Memory Routing agent, built as a LangGraph state machine.

Flow (each is a node):
    receive_query -> intent_detection -> memory_router -> retriever
      -> re_ranker -> context_builder -> llm_response -> memory_update

The whole point of this phase is the ROUTING: intent_detection classifies the
query into one or more memory types, and memory_router turns that into the
Pinecone namespace(s) we actually search so we retrieve only from the
relevant memory instead of everything.
"""

import json
import re
from functools import lru_cache

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from backend.database.session import SessionLocal
from backend.embeddings.model import embed_query
from backend.embeddings.store import MEMORY_NAMESPACES, search_namespace
from backend.llm.client import get_llm
from backend.llm.context import build_context
from backend.llm.rag import SYSTEM_PROMPT_TEXT, answer_with_context
from backend.memory_writer import store_memory
from backend.prompts import classifier_version, load_classifier_prompt

VALID_TYPES = list(MEMORY_NAMESPACES.keys())  # document, code, decision, workflow, conversation

PER_NAMESPACE_TOP_K = 4    # how many hits to pull from each selected namespace
DEFAULT_FINAL_TOP_K = 4    # how many to keep after merging + re-ranking


class GraphState(TypedDict, total=False):
    query: str
    project_id: int | None
    final_top_k: int
    history: list[str]         # recent "role: content" lines for this project
    intent: list[str]          # memory types chosen by the classifier
    namespaces: list[str]      # the Pinecone namespaces those map to
    retrieved: list[dict]      # raw hits from all selected namespaces
    reranked: list[dict]       # merged + score-sorted + trimmed
    context: str               # the token-budgeted context string
    context_trace: dict        # what was kept/dropped + token breakdown
    answer: str
    memory_update_result: dict  # what (if anything) got saved back (node is named memory_update)


# --- intent classifier (its own small chain) ------------------------------

from langchain_core.output_parsers import StrOutputParser  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402

@lru_cache(maxsize=8)
def _classifier_template(version: str) -> ChatPromptTemplate:
    # The system text now comes from a versioned file in backend/prompts/,
    # selectable via CLASSIFIER_PROMPT_VERSION. Cached per version so we don't
    # re-read the file on every call.
    system_text = load_classifier_prompt(version)
    return ChatPromptTemplate.from_messages([("system", system_text), ("human", "{query}")])


def classify_intent(query: str, version: str | None = None) -> list[str]:
    version = version or classifier_version()
    chain = _classifier_template(version) | get_llm() | StrOutputParser()
    raw = chain.invoke({"query": query})
    picked = [tok for tok in re.split(r"[^a-z]+", raw.lower()) if tok in VALID_TYPES]
    # de-dupe, preserve order
    seen, ordered = set(), []
    for t in picked:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    # Fall back to the most general type if the classifier returned nothing usable.
    return ordered or ["document"]


# --- memory_update decision (its own small chain) --------------------------

_MEMORY_UPDATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You decide whether a chat exchange should be saved as a NEW long-term "
            "memory.\n"
            "Rule: look at the USER'S MESSAGE only. If it is a QUESTION (asks "
            "what/why/how/who/when, or ends with '?'), set save=false no matter "
            "what the answer says. Save=true ONLY when the user's message is a "
            "DECLARATIVE statement that introduces new information worth keeping "
            "(e.g. 'We decided to...', 'The new release process is...', "
            "'Remember that...').\n"
            "Respond with STRICT JSON and nothing else:\n"
            '{{"save": true|false, "memory_type": one of '
            '["document","code","decision","workflow","conversation"] or null, '
            '"content": "concise statement to store" or null}}',
        ),
        ("human", "User message:\n{question}\n\nAssistant answer:\n{answer}"),
    ]
)


def _extract_json(raw: str) -> dict:
    # LLMs sometimes wrap JSON in ```json fences or add stray text; grab the
    # first {...} block and parse that.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(match.group(0)) if match else {}


# --- the eight nodes -------------------------------------------------------

def receive_query(state: GraphState) -> dict:
    # Normalize input and set defaults. (A real system might also strip PII,
    # enforce length limits, etc. kept minimal here.)
    return {
        "query": state["query"].strip(),
        "final_top_k": state.get("final_top_k") or DEFAULT_FINAL_TOP_K,
    }


def intent_detection(state: GraphState) -> dict:
    return {"intent": classify_intent(state["query"])}


def memory_router(state: GraphState) -> dict:
    # Turn the chosen memory types into the concrete namespaces to search.
    return {"namespaces": [MEMORY_NAMESPACES[t] for t in state["intent"]]}


def retriever(state: GraphState) -> dict:
    query_embedding = embed_query(state["query"])
    project_id = state.get("project_id")
    retrieved: list[dict] = []
    for memory_type, namespace in zip(state["intent"], state["namespaces"]):
        # Scope retrieval to the current project so a project only sees its own
        # memories/documents.
        for hit in search_namespace(namespace, query_embedding, PER_NAMESPACE_TOP_K, project_id=project_id):
            hit["memory_type"] = memory_type  # tag with the type we queried it from
            retrieved.append(hit)
    return {"retrieved": retrieved}


def re_ranker(state: GraphState) -> dict:
    # If more than one namespace was hit, results are interleaved merge them
    # and sort by score (cosine similarity is comparable across namespaces
    # since every type uses the same embedding model + metric), keep the best.
    ranked = sorted(state["retrieved"], key=lambda r: r["score"], reverse=True)
    return {"reranked": ranked[: state["final_top_k"]]}


def context_builder(state: GraphState) -> dict:
    # Phase 7: real context engineering. Fit conversation history + retrieved
    # chunks into a TOKEN budget (not a character count), and record exactly
    # what was kept vs. dropped so /context-trace can report it.
    context, trace = build_context(
        SYSTEM_PROMPT_TEXT,
        state.get("reranked", []),
        state.get("history", []),
    )
    return {"context": context, "context_trace": trace}


def llm_response(state: GraphState) -> dict:
    context = state.get("context", "")
    chunks = [context] if context.strip() else []
    return {"answer": answer_with_context(state["query"], chunks)}


def memory_update(state: GraphState) -> dict:
    # If the exchange recorded a new decision/fact, save it to the right memory
    # type. Conservative by design: any error or ambiguity -> don't save.
    result = {"saved": False}
    try:
        chain = _MEMORY_UPDATE_PROMPT | get_llm() | StrOutputParser()
        raw = chain.invoke({"question": state["query"], "answer": state.get("answer", "")})
        data = _extract_json(raw)
        if data.get("save") and data.get("memory_type") in VALID_TYPES and data.get("content"):
            db = SessionLocal()
            try:
                memory = store_memory(
                    db,
                    data["memory_type"],
                    data["content"],
                    source_ref="chat",
                    project_id=state.get("project_id"),
                )
                result = {
                    "saved": memory is not None,
                    "memory_type": data["memory_type"],
                    "memory_id": memory.id if memory else None,
                    "content": data["content"],
                }
            finally:
                db.close()
    except Exception:
        result = {"saved": False}
    return {"memory_update_result": result}


# --- assemble + compile the graph once at import --------------------------

def _build_graph():
    g = StateGraph(GraphState)
    g.add_node("receive_query", receive_query)
    g.add_node("intent_detection", intent_detection)
    g.add_node("memory_router", memory_router)
    g.add_node("retriever", retriever)
    g.add_node("re_ranker", re_ranker)
    g.add_node("context_builder", context_builder)
    g.add_node("llm_response", llm_response)
    g.add_node("memory_update", memory_update)

    g.set_entry_point("receive_query")
    g.add_edge("receive_query", "intent_detection")
    g.add_edge("intent_detection", "memory_router")
    g.add_edge("memory_router", "retriever")
    g.add_edge("retriever", "re_ranker")
    g.add_edge("re_ranker", "context_builder")
    g.add_edge("context_builder", "llm_response")
    g.add_edge("llm_response", "memory_update")
    g.add_edge("memory_update", END)
    return g.compile()


GRAPH = _build_graph()


def run_chat_graph(
    query: str,
    project_id: int | None = None,
    final_top_k: int = DEFAULT_FINAL_TOP_K,
    history: list[str] | None = None,
) -> GraphState:
    return GRAPH.invoke(
        {
            "query": query,
            "project_id": project_id,
            "final_top_k": final_top_k,
            "history": history or [],
        }
    )
