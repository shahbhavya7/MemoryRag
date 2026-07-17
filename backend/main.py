from fastapi import FastAPI

from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.chats import router as chats_router
from backend.api.context_trace import router as context_trace_router
from backend.api.documents import router as documents_router
from backend.api.memories import router as memories_router
from backend.api.projects import router as projects_router
from backend.database.session import Base, SessionLocal, engine
from backend.embeddings.store import ensure_index_exists
from backend.models import chat, context_trace, memory, message, project, user  # noqa: F401  ensures models are registered before create_all
from backend.models.memory import seed_memory_types

Base.metadata.create_all(bind=engine)
ensure_index_exists()

# Make sure the five memory types exist in Postgres (idempotent).
_db = SessionLocal()
try:
    seed_memory_types(_db)
finally:
    _db.close()

app = FastAPI(title="MemoryRAG API", version="0.1.0")

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(chats_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(memories_router)
app.include_router(context_trace_router)


@app.get("/health")
def health():
    return {"status": "ok"}
