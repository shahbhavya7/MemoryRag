"""Phase 8 demo — ingest THIS project's own git history, then ask about it.

What it proves: real commits become searchable Code Memory (and Decision Memory
for "why" commits), and a chat answer can cite the exact commit hash(es) it drew
from.

Usage (API must be running — see README):
    python3 demo/demo_phase8.py [base_url]

Steps:
  1. POST /ingest/git for this repo -> prints what was ingested per commit.
  2. Ask a few questions via POST /chat and print the answer PLUS the commit
     hash(es) cited in the sources.
"""

import os
import sys
import time

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"

# This repo's root = the parent of the demo/ folder this file lives in.
REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Questions aimed at commit messages/diffs that actually exist in this repo's
# history. Phrased as "in the code history..." so the router sends them to CODE
# memory, where the full diffs live (that's where the detail is).
QUESTIONS = [
    "In the code history, what changed when adaptive memory routing with LangGraph was added?",
    "In the code history, what changed when the multi-memory split with isolated namespaces was added?",
    "According to the commits, what was done to add embeddings and vector search?",
]


def ingest() -> dict:
    print(f"Ingesting git history from: {REPO_PATH}\n")
    resp = requests.post(f"{BASE_URL}/ingest/git", json={"repo_path": REPO_PATH})
    resp.raise_for_status()
    summary = resp.json()
    print(
        f"Processed {summary['commits_processed']} commit(s): "
        f"{summary['code_chunks_stored']} code chunk(s), "
        f"{summary['decision_entries_stored']} decision entry(ies).\n"
    )
    for c in summary["commits"]:
        tag = "  [+decision]" if c["stored_as_decision"] else ""
        print(f"  {c['short_sha']}  {c['subject']}{tag}")
    print()
    return summary


def ask(question: str) -> None:
    # Retry once — Pinecone is eventually consistent right after an upsert.
    for attempt in range(2):
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"project_id": 1, "message": question},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("sources"):
            break
        time.sleep(3)

    print("=" * 70)
    print(f"Q: {question}")
    print(f"Routed to memory: {data.get('memory_types')}")
    print(f"\nA: {data.get('answer')}\n")

    cited = []
    for s in data.get("sources", []):
        ref = s.get("source_ref")
        if ref:
            short = ref[:8]
            cited.append(f"{short} (score {s['score']:.3f}, {s.get('memory_type')})")
    if cited:
        print("Cited commit(s):")
        for c in cited:
            print(f"  - {c}")
    else:
        print("Cited commit(s): (none returned)")
    print()


def main() -> None:
    ingest()
    print(
        "Note: git diff chunks are large (~800 tokens each), so grounded answers\n"
        "need a healthy CONTEXT_TOKEN_BUDGET (e.g. 1500-2000). If answers come back\n"
        "'I don't know', your budget is likely too small to fit a whole commit.\n"
    )
    print("Waiting a few seconds for the vector index to settle...\n")
    time.sleep(5)
    for q in QUESTIONS:
        ask(q)


if __name__ == "__main__":
    main()
