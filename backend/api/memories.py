from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.embeddings.model import embed_query
from backend.embeddings.store import search_memories
from backend.memory_writer import store_memory
from backend.models.memory import MemoryType
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
    # Validate the type name up front so a bad type returns a clear 400.
    _get_memory_type_or_400(db, payload.memory_type)
    memory = store_memory(db, payload.memory_type, payload.content, payload.source_ref)
    return MemoryOut(
        id=memory.id,
        memory_type=payload.memory_type,
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
