from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Session

from backend.database.session import Base

# The five memory types and the Pinecone namespace each one is stored in.
# This list is the single source of truth for "what memory types exist."
MEMORY_TYPE_DEFS = [
    {"name": "document", "namespace": "document_memory", "description": "PDFs, docs, notes, wiki pages — general knowledge."},
    {"name": "code", "namespace": "code_memory", "description": "Functions, classes, APIs, READMEs — understanding codebases."},
    {"name": "decision", "namespace": "decision_memory", "description": "Structured engineering decisions and their reasoning."},
    {"name": "workflow", "namespace": "workflow_memory", "description": "Business/engineering processes and step-by-step flows."},
    {"name": "conversation", "namespace": "conversation_memory", "description": "Important discussions worth remembering long-term."},
]


class MemoryType(Base):
    __tablename__ = "memory_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    namespace = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    memory_type_id = Column(Integer, ForeignKey("memory_types.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_ref = Column(String, nullable=True)
    # Which Pinecone vector this row corresponds to — the relational link
    # between "what we stored" (Postgres) and "where its embedding lives" (Pinecone).
    vector_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def seed_memory_types(db: Session) -> None:
    # Idempotent: insert any of the five types that aren't already present, so
    # this is safe to run on every startup.
    existing = {mt.name for mt in db.query(MemoryType).all()}
    for definition in MEMORY_TYPE_DEFS:
        if definition["name"] not in existing:
            db.add(MemoryType(**definition))
    db.commit()
