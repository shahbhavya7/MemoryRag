"""Phase 8 — endpoint to trigger git-history ingestion into memory.

POST /ingest/git {"repo_path": "...", "max_commits": 50}

Walks the given local repo's commits and stores them into code memory (and
decision memory for "why" commits), each tagged with its commit hash. This is
the HTTP twin of `python -m backend.services.git_ingest`.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.schemas import GitIngestRequest, GitIngestResponse
from backend.services.git_ingest import ingest_git_repo

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/git", response_model=GitIngestResponse)
def ingest_git(payload: GitIngestRequest, db: Session = Depends(get_db)):
    try:
        summary = ingest_git_repo(
            db,
            payload.repo_path,
            max_commits=payload.max_commits,
            branch=payload.branch,
        )
    except ValueError as exc:
        # Bad repo path / not a git repo -> clear 400 instead of a 500.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GitIngestResponse(**summary)
