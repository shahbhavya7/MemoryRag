"""Proves the Phase 6 Adaptive Memory Routing graph picks the RIGHT memory type.

Usage:
    python3 demo/demo_phase6.py [base_url]

Requires the API running with PINECONE_API_KEY + LLM_PROVIDER/LLM_API_KEY set.

The proof point of this phase is the ROUTING decision, not the final answer
text. So this seeds one distinctive entry per memory type, then asks five
questions each clearly aimed at a different type and prints which memory
type(s) the router chose for each. It asserts each question routed to its
expected type.
"""

import sys
import time

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# One clearly-typed seed per memory type, so a correct answer proves the
# router reached into the right namespace.
SEED = {
    "document": "The office WiFi network is called 'Halden-Guest' and the password rotates every Monday morning.",
    "code": "The function slugify(title) lowercases the title, replaces spaces with hyphens, and strips punctuation.",
    "decision": "We decided to use PostgreSQL instead of MongoDB because our data is highly relational and we need transactions.",
    "workflow": "To release the mobile app: bump the version, run the test suite, upload the build to TestFlight, then submit for review.",
    "conversation": "In the retro, the team agreed to stop doing Friday deploys after two incidents happened over the weekend.",
}

# Each question is aimed at exactly one memory type. (question, expected_type)
QUESTIONS = [
    ("Why did we pick PostgreSQL over MongoDB?", "decision"),
    ("What are the steps to release the mobile app?", "workflow"),
    ("What does the slugify function do?", "code"),
    ("What is the office WiFi network name?", "document"),
    ("What did the team agree about Friday deploys in the retro?", "conversation"),
]


def seed() -> None:
    print("Seeding one distinctive entry per memory type...")
    for memory_type, content in SEED.items():
        r = requests.post(
            f"{BASE_URL}/memories",
            json={"memory_type": memory_type, "content": content, "source_ref": f"seed/{memory_type}"},
        )
        r.raise_for_status()
    print("Seed complete.")


def wait_for_settle() -> None:
    # Poll until EVERY namespace returns its seed Pinecone serverless is
    # eventually consistent and different namespaces can settle at different
    # times, so checking just one isn't enough.
    print("\nWaiting for all five vector namespaces to settle...")
    for _ in range(18):
        ready = []
        for memory_type in SEED:
            r = requests.post(f"{BASE_URL}/memories/search",
                              json={"memory_type": memory_type, "query": "x", "top_k": 1})
            ready.append(bool(r.ok and r.json()["results"]))
        if all(ready):
            print("All namespaces settled.\n")
            return
        time.sleep(5)
    print("Proceeding (some namespaces may still be settling).\n")


def main() -> None:
    seed()
    wait_for_settle()

    print("=" * 72)
    print("ROUTING TEST: each question is aimed at one memory type.")
    print("The proof is which memory type the router PICKS, shown per question.")
    print("=" * 72)

    passed = 0
    for question, expected in QUESTIONS:
        body = None
        # Retry once if retrieval transiently returns nothing (Pinecone
        # eventual consistency on freshly-seeded vectors).
        for attempt in range(2):
            r = requests.post(f"{BASE_URL}/chat", json={"project_id": 1, "message": question})
            r.raise_for_status()
            body = r.json()
            if body["sources"]:
                break
            time.sleep(4)
        routed = body["memory_types"]
        ok = expected in routed
        passed += ok
        print(f"\nQ: {question}")
        print(f"   router picked : {routed}   (expected '{expected}')  [{'OK' if ok else 'MISROUTED'}]")
        print(f"   answer        : {body['answer'][:200]}")
        top = body["sources"][0] if body["sources"] else None
        if top:
            print(f"   top source    : ({top.get('memory_type')}) {top['text'][:90]}...")

    print("\n" + "=" * 72)
    print(f"Routed correctly on {passed}/{len(QUESTIONS)} questions.")
    if passed != len(QUESTIONS):
        raise SystemExit("Some questions were misrouted see above.")
    print("PASSED: every question was routed to its intended memory type.")

    # Bonus: prove the last node (memory_update) actually writes back when the
    # user STATES something new (as opposed to asking a question).
    print("\n" + "=" * 72)
    print("BONUS memory_update node: state a NEW decision and watch it get saved.")
    print("=" * 72)
    statement = "We decided to adopt trunk-based development so we stop maintaining long-lived feature branches."
    r = requests.post(f"{BASE_URL}/chat", json={"project_id": 1, "message": statement})
    r.raise_for_status()
    update = r.json().get("memory_update") or {}
    print(f"\nUser stated: {statement}")
    print(f"memory_update node result: {update}")
    if update.get("saved"):
        print(f"SAVED to '{update.get('memory_type')}' memory (id={update.get('memory_id')}) the graph learned a new fact.")
    else:
        print("(Not saved the model judged it not worth storing.)")


if __name__ == "__main__":
    main()
