from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.llm.graph import run_chat_graph
from backend.models.message import Message
from backend.schemas import ChatRequest, ChatResponse, ChatSource

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    # Phase 6: /chat now runs the Adaptive Memory Routing graph end to end
    # (intent detection -> routing -> retrieval -> re-rank -> context -> answer
    # -> memory update) instead of the Phase 4 single-collection retrieval.
    final = run_chat_graph(payload.message, project_id=payload.project_id, final_top_k=payload.top_k)

    answer = final.get("answer", "")

    # Log the exchange (both sides) so the conversation is persisted.
    db.add(Message(project_id=payload.project_id, role="user", content=payload.message))
    db.add(Message(project_id=payload.project_id, role="assistant", content=answer))
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
    )
