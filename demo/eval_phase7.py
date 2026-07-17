"""Routing-accuracy evaluation — the project's first real retrieval-quality metric.

Usage:
    python3 demo/eval_phase7.py

Runs a fixed set of hand-written (question -> expected memory type) pairs
through the intent router and reports accuracy. It evaluates BOTH classifier
prompt versions (v1 and v2) so you can see, as a number, whether a prompt
change actually helped — instead of eyeballing a few examples ("vibe check").

This calls the router directly (no server, no Pinecone/Postgres writes) — it
only needs LLM_API_KEY set. Run it from the repo root with the env loaded:
    set -a; source .env; set +a
    python3 demo/eval_phase7.py

Note: routing uses an LLM classifier, so results can vary slightly run to run.
"""

import os
import sys

# Make `backend` importable when run as `python3 demo/eval_phase7.py`.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.llm.graph import classify_intent  # noqa: E402

# Hand-labeled gold set: 2 per memory type. These are the "right answers" a
# human decided on — the yardstick the router is measured against.
GOLD = [
    ("Why did we choose PostgreSQL over MongoDB?", "decision"),
    ("What were the tradeoffs of switching to JWT auth?", "decision"),
    ("How do we deploy the backend to production?", "workflow"),
    ("What are the steps to onboard a new hire?", "workflow"),
    ("What does the slugify function do?", "code"),
    ("How many times does the RetryClient retry a failed call?", "code"),
    ("What is the office WiFi network name?", "document"),
    ("What is the meal reimbursement limit in the expense policy?", "document"),
    ("What did the team agree about Friday deploys in the retro?", "conversation"),
    ("What was decided about the mobile app in the Q2 planning call?", "conversation"),
]


def evaluate(version: str) -> float:
    print(f"\n=== classifier prompt {version} ===")
    correct = 0
    for question, expected in GOLD:
        routed = classify_intent(question, version=version)
        ok = expected in routed
        correct += ok
        mark = "OK  " if ok else "MISS"
        print(f"  [{mark}] expected {expected:<12} got {routed}  <- {question}")
    accuracy = correct / len(GOLD)
    print(f"  accuracy: {correct}/{len(GOLD)} = {accuracy:.0%}")
    return accuracy


def main() -> None:
    print("Routing-accuracy evaluation over", len(GOLD), "hand-labeled questions.")
    acc_v1 = evaluate("v1")
    acc_v2 = evaluate("v2")

    print("\n" + "=" * 60)
    print(f"v1 accuracy: {acc_v1:.0%}")
    print(f"v2 accuracy: {acc_v2:.0%}")
    if acc_v2 > acc_v1:
        print("v2 beats v1 — the prompt change measurably improved routing.")
    elif acc_v2 == acc_v1:
        print("v1 and v2 tied on this set.")
    else:
        print("v1 scored higher on this run (LLM classifiers vary run to run).")
    print("This is a real metric you can track as prompts/retrieval change.")


if __name__ == "__main__":
    main()
