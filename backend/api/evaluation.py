"""Phase 9d — run the routing-accuracy evaluation on demand, return JSON.

POST /evaluation/run  ->  runs the Phase 7 gold set through the intent router
and reports overall accuracy, a per-memory-type breakdown, and the per-question
expected-vs-predicted results (so the UI can highlight mismatches).

This makes real LLM classifier calls (one per gold question), so it takes a few
seconds — it's an on-demand action behind a button, not something on page load.
"""

from fastapi import APIRouter

from backend.eval_data import GOLD
from backend.llm.graph import classify_intent
from backend.prompts import classifier_version
from backend.schemas import EvalPerType, EvalQuestionResult, EvalResponse

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvalResponse)
def run_evaluation(version: str | None = None):
    version = version or classifier_version()

    results: list[EvalQuestionResult] = []
    per_type: dict[str, dict[str, int]] = {}
    correct = 0

    for question, expected in GOLD:
        predicted = classify_intent(question, version=version)
        ok = expected in predicted
        correct += int(ok)
        results.append(
            EvalQuestionResult(question=question, expected=expected, predicted=predicted, correct=ok)
        )
        bucket = per_type.setdefault(expected, {"total": 0, "correct": 0})
        bucket["total"] += 1
        bucket["correct"] += int(ok)

    total = len(GOLD)
    breakdown = [
        EvalPerType(
            memory_type=mt,
            total=b["total"],
            correct=b["correct"],
            accuracy=(b["correct"] / b["total"]) if b["total"] else 0.0,
        )
        for mt, b in per_type.items()
    ]

    return EvalResponse(
        version=version,
        total=total,
        correct=correct,
        accuracy=(correct / total) if total else 0.0,
        per_type=breakdown,
        results=results,
    )
