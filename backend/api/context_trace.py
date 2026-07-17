import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.context_trace import ContextTrace
from backend.schemas import ContextTraceOut

router = APIRouter(tags=["context-trace"])


@router.get("/context-trace/{message_id}", response_model=ContextTraceOut)
def get_context_trace(message_id: int, db: Session = Depends(get_db)):
    # Exactly what the LLM was given for this answer: what got retrieved, what
    # was kept vs. dropped under the token budget, and the token breakdown.
    row = (
        db.query(ContextTrace)
        .filter(ContextTrace.message_id == message_id)
        .order_by(ContextTrace.id.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No context trace for message_id {message_id}")

    trace = json.loads(row.trace_json)
    return ContextTraceOut(message_id=message_id, **trace)
