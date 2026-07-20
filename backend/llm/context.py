"""Real context engineering: token counting + a token budget split across
system prompt / conversation history / retrieved context.

Phase 6 truncated context by a raw CHARACTER count, which is crude a
character isn't the unit an LLM actually pays for or is limited by. Phase 7
counts real TOKENS (via tiktoken) and divides a fixed token budget between the
three things competing for space in the prompt, keeping the highest-value
pieces and reporting exactly what was kept vs. dropped (the context trace).
"""

import os

import tiktoken

# cl100k_base is OpenAI's tokenizer. Our LLM is a Llama model via Groq, so this
# is an approximation of its true token counts but it's a stable, good-enough
# yardstick for *budgeting* (the goal is a consistent limit, not billing).
_ENCODING = tiktoken.get_encoding("cl100k_base")

# Total token budget for the variable parts of the prompt.
TOTAL_TOKEN_BUDGET = int(os.getenv("CONTEXT_TOKEN_BUDGET", "1200"))
# Share of the post-system budget reserved for conversation history.
HISTORY_FRACTION = 0.25


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def build_context(
    system_prompt: str,
    reranked: list[dict],
    history: list[str],
    total_budget: int = TOTAL_TOKEN_BUDGET,
) -> tuple[str, dict]:
    """Fit history + retrieved chunks into a token budget.

    Returns (context_string, trace) where the trace is the exact accounting
    that GET /context-trace/{message_id} exposes.
    """
    system_tokens = count_tokens(system_prompt)
    remaining = max(0, total_budget - system_tokens)
    history_budget = int(remaining * HISTORY_FRACTION)

    # --- fit conversation history (most recent first) ---
    kept_history, history_tokens = [], 0
    for message in reversed(history):  # history is oldest->newest; prefer newest
        t = count_tokens(message)
        if history_tokens + t <= history_budget:
            kept_history.append(message)
            history_tokens += t
        else:
            break
    kept_history.reverse()  # restore chronological order

    # --- fit retrieved chunks (already score-sorted) into what's left ---
    context_budget = remaining - history_tokens
    kept_texts, retrieved_trace = [], []
    context_tokens = 0
    for hit in reranked:
        text = hit["text"]
        t = count_tokens(text)
        fits = context_tokens + t <= context_budget
        if fits:
            kept_texts.append(text)
            context_tokens += t
        retrieved_trace.append(
            {
                "memory_type": hit.get("memory_type"),
                "score": hit.get("score", 0.0),
                "tokens": t,
                "kept": fits,
                "preview": text[:120].replace("\n", " "),
            }
        )

    # --- assemble the final context string ---
    parts = []
    if kept_history:
        parts.append("Recent conversation:\n" + "\n".join(kept_history))
    if kept_texts:
        parts.append("\n\n---\n\n".join(kept_texts))
    context_string = "\n\n===\n\n".join(parts)

    trace = {
        "token_budget": total_budget,
        "tokens": {
            "system": system_tokens,
            "history": history_tokens,
            "context": context_tokens,
            "total": system_tokens + history_tokens + context_tokens,
        },
        "history_messages_available": len(history),
        "history_messages_kept": len(kept_history),
        "retrieved": retrieved_trace,
        "kept_count": sum(1 for r in retrieved_trace if r["kept"]),
        "dropped_count": sum(1 for r in retrieved_trace if not r["kept"]),
    }
    return context_string, trace
