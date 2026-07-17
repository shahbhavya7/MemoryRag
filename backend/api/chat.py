import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.llm.graph import run_chat_graph
from backend.models.context_trace import ContextTrace
from backend.models.message import Message
from backend.schemas import ChatRequest, ChatResponse, ChatSource

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 6  # how many recent messages to offer as conversation history


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    # Load recent conversation history for this project (before logging the new
    # message), so the context builder can budget space for it.
    recent = (
        db.query(Message)
        .filter(Message.project_id == payload.project_id)
        .order_by(Message.id.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    history = [f"{m.role}: {m.content}" for m in reversed(recent)]

    # Phase 6+7: run the routing graph (intent -> route -> retrieve -> re-rank
    # -> token-budgeted context -> answer -> memory update).
    final = run_chat_graph(
        payload.message,
        project_id=payload.project_id,
        final_top_k=payload.top_k,
        history=history,
    )
    answer = final.get("answer", "")

    # Log the exchange (both sides).
    db.add(Message(project_id=payload.project_id, role="user", content=payload.message))
    assistant_message = Message(project_id=payload.project_id, role="assistant", content=answer)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # Persist the context trace, keyed to the assistant message it explains.
    trace = final.get("context_trace")
    if trace is not None:
        db.add(ContextTrace(message_id=assistant_message.id, trace_json=json.dumps(trace)))
        db.commit()

    sources = [
        ChatSource(
            text=hit["text"],
            score=hit["score"],
            memory_type=hit.get("memory_type"),
            source_ref=hit.get("source_ref"),
        )
        for hit in final.get("reranked", [])
    ]
    return ChatResponse(
        answer=answer,
        memory_types=final.get("intent", []),
        sources=sources,
        memory_update=final.get("memory_update_result"),
        message_id=assistant_message.id,
    )
