from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.embeddings.model import embed_query
from backend.embeddings.store import add_memory_vector, search_memories
from backend.models.memory import Memory, MemoryType
from backend.schemas import (
    MemoryCreate,
    MemoryOut,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
)

router = APIRouter(prefix="/memories", tags=["memories"])


def _get_memory_type_or_400(db: Session, name: str) -> MemoryType:
    memory_type = db.query(MemoryType).filter(MemoryType.name == name).first()
    if memory_type is None:
        valid = [mt.name for mt in db.query(MemoryType).order_by(MemoryType.id).all()]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown memory_type '{name}'. Valid types: {', '.join(valid)}.",
        )
    return memory_type


@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    memory_type = _get_memory_type_or_400(db, payload.memory_type)

    # 1. Save the relational row first so we have its id to tie the vector back to.
    memory = Memory(
        memory_type_id=memory_type.id,
        content=payload.content,
        source_ref=payload.source_ref,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    # 2. Embed the content and upsert into THIS type's namespace only.
    embedding = embed_query(payload.content)
    vector_id = add_memory_vector(
        namespace=memory_type.namespace,
        embedding=embedding,
        memory_id=memory.id,
        memory_type=memory_type.name,
        content=payload.content,
        source_ref=payload.source_ref,
    )

    # 3. Record which vector this row maps to.
    memory.vector_id = vector_id
    db.commit()
    db.refresh(memory)

    return MemoryOut(
        id=memory.id,
        memory_type=memory_type.name,
        content=memory.content,
        source_ref=memory.source_ref,
        created_at=memory.created_at,
    )


@router.post("/search", response_model=MemorySearchResponse)
def search_memory(payload: MemorySearchRequest, db: Session = Depends(get_db)):
    # Look up the namespace for the requested type and search ONLY that
    # namespace — this is the direct, un-routed search Phase 5 is about.
    memory_type = _get_memory_type_or_400(db, payload.memory_type)
    query_embedding = embed_query(payload.query)
    results = search_memories(memory_type.namespace, query_embedding, payload.top_k)
    return MemorySearchResponse(results=[MemorySearchResult(**r) for r in results])
