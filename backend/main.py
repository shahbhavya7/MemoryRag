from fastapi import FastAPI

from backend.api.auth import router as auth_router
from backend.api.chats import router as chats_router
from backend.api.documents import router as documents_router
from backend.api.projects import router as projects_router
from backend.database.session import Base, engine
from backend.embeddings.store import ensure_index_exists
from backend.models import chat, project, user  # noqa: F401  ensures models are registered before create_all

Base.metadata.create_all(bind=engine)
ensure_index_exists()

app = FastAPI(title="MemoryRAG API", version="0.1.0")

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(chats_router)
app.include_router(documents_router)


@app.get("/health")
def health():
    return {"status": "ok"}
