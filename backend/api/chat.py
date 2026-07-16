from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.embeddings.model import embed_query
from backend.embeddings.store import search
from backend.llm.rag import answer_with_context
from backend.models.message import Message
from backend.schemas import ChatRequest, ChatResponse, ChatSource

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    # 1. Retrieve: embed the question and pull the most similar chunks for THIS project.
    query_embedding = embed_query(payload.message)
    retrieved = search(query_embedding, payload.top_k, project_id=payload.project_id)

    # 2. Generate: feed the retrieved chunk texts to the LangChain RAG chain.
    chunk_texts = [r["text"] for r in retrieved]
    answer = answer_with_context(payload.message, chunk_texts)

    # 3. Log the exchange (both sides) so the conversation is persisted.
    db.add(Message(project_id=payload.project_id, role="user", content=payload.message))
    db.add(Message(project_id=payload.project_id, role="assistant", content=answer))
    db.commit()

    sources = [
        ChatSource(
            text=r["text"],
            score=r["score"],
            source_filename=r["metadata"]["source_filename"],
        )
        for r in retrieved
    ]
    return ChatResponse(answer=answer, sources=sources)
