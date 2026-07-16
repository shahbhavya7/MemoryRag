"""Proves the five memory-type namespaces are truly ISOLATED, not just labeled.

Usage:
    python3 demo/demo_phase5.py [base_url]

Requires the API to be running (see README).

The strong test isn't "search decision memory, get decisions back" — that
could just be labeling. The real test is: search ONE type's namespace using a
query that semantically matches a DIFFERENT type's content, and confirm you
STILL only ever get that one type's entries. If namespaces are really
isolated, the other type's content simply isn't reachable there — even when
it would have been the best match overall.

This seeds its own known entries first (reusing seed_phase5's data), so it's
self-contained.
"""

import sys
import time

import requests

# demo/ is on sys.path[0] when this script is run directly, so we can reuse
# the same seed data instead of duplicating it.
from seed_phase5 import SEED_ENTRIES

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

MEMORY_TYPES = list(SEED_ENTRIES.keys())

# A query that clearly "belongs" to each type — phrased loosely, not quoting
# the seeded text, so matching depends on meaning.
PROBES = {
    "document": "what is the company travel and hotel policy",
    "code": "function that cleans up an email address",
    "decision": "why did we choose stateless token authentication",
    "workflow": "steps to ship the backend to production",
    "conversation": "what did the team decide about the mobile app in planning",
}


def seed() -> None:
    print("Seeding example memories across all five types...")
    for memory_type, entries in SEED_ENTRIES.items():
        for entry in entries:
            r = requests.post(f"{BASE_URL}/memories", json={"memory_type": memory_type, **entry})
            r.raise_for_status()
    print("Seed complete.")


def search(memory_type: str, query: str, top_k: int = 5) -> list[dict]:
    r = requests.post(
        f"{BASE_URL}/memories/search",
        json={"memory_type": memory_type, "query": query, "top_k": top_k},
    )
    r.raise_for_status()
    return r.json()["results"]


def wait_for_settle() -> None:
    # Pinecone serverless is eventually consistent right after upserts
    # (same as Phase 3/4). Poll until the document namespace returns its seed.
    print("\nWaiting for the vector namespaces to settle...")
    for _ in range(12):
        if search("document", PROBES["document"], top_k=1):
            print("Settled.\n")
            return
        time.sleep(5)
    print("Proceeding (namespaces may still be settling).\n")


def main() -> None:
    seed()
    wait_for_settle()

    print("=" * 70)
    print("ISOLATION MATRIX: search every namespace with every type's probe.")
    print("Each cell shows the memory_type(s) actually returned by that search.")
    print("A correctly isolated namespace ONLY ever returns its own type.")
    print("=" * 70)

    violations = []
    for ns_type in MEMORY_TYPES:
        for probe_type in MEMORY_TYPES:
            results = search(ns_type, PROBES[probe_type])
            returned_types = {r["memory_type"] for r in results}

            # THE isolation assertion: no matter which probe we used, searching
            # the ns_type namespace must only ever return ns_type entries.
            leaked = returned_types - {ns_type}
            tag = "OK" if not leaked else f"LEAK -> {leaked}"
            if leaked:
                violations.append((ns_type, probe_type, leaked))
            print(f"  search {ns_type:<12} with {probe_type:<12} probe -> returned {returned_types or '{}'}  [{tag}]")

    print("\n" + "=" * 70)
    print("SPOTLIGHT: the 'deploy to production' query is a WORKFLOW question.")
    print("Only workflow_memory should surface the deploy runbook; other")
    print("namespaces must not contain it at all.")
    print("=" * 70)
    for ns_type in MEMORY_TYPES:
        top = search(ns_type, PROBES["workflow"], top_k=1)
        best = top[0]["content"][:70].replace("\n", " ") if top else "(nothing)"
        print(f"  best hit in {ns_type:<12}: {best}")

    print()
    if violations:
        print(f"FAILED: {len(violations)} cross-type leak(s) detected: {violations}")
        raise SystemExit(1)
    print("PASSED: every namespace returned ONLY its own memory type across all "
          f"{len(MEMORY_TYPES) ** 2} searches — the five memory types are truly isolated.")


if __name__ == "__main__":
    main()
