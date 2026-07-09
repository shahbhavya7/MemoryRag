from fastapi import FastAPI

from backend.api.projects import router as projects_router
from backend.database.session import Base, engine
from backend.models import project  # noqa: F401  ensures model is registered before create_all

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MemoryRAG API", version="0.1.0")

app.include_router(projects_router)


@app.get("/health")
def health():
    return {"status": "ok"}
