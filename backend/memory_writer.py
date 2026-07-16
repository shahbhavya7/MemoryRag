from sqlalchemy.orm import Session

from backend.embeddings.model import embed_query
from backend.embeddings.store import add_memory_vector
from backend.models.memory import Memory, MemoryType

# Shared "write one memory entry" logic used by BOTH the POST /memories
# endpoint and the graph's memory_update node, so the save path lives in one
# place. Returns the created Memory, or None if the type name is unknown.


def store_memory(db: Session, memory_type_name: str, content: str, source_ref: str | None = None) -> Memory | None:
    memory_type = db.query(MemoryType).filter(MemoryType.name == memory_type_name).first()
    if memory_type is None:
        return None

    # 1. Save the relational row first so we have its id to tie the vector back to.
    memory = Memory(memory_type_id=memory_type.id, content=content, source_ref=source_ref)
    db.add(memory)
    db.commit()
    db.refresh(memory)

    # 2. Embed the content and upsert into THIS type's namespace only.
    embedding = embed_query(content)
    vector_id = add_memory_vector(
        namespace=memory_type.namespace,
        embedding=embedding,
        memory_id=memory.id,
        memory_type=memory_type.name,
        content=content,
        source_ref=source_ref,
    )

    # 3. Record which vector this row maps to.
    memory.vector_id = vector_id
    db.commit()
    db.refresh(memory)
    return memory
