"""Seeds a rich set of typed memories so you can test Phase 6 routing yourself.

Usage:
    python3 demo/seed_phase6.py [base_url] [project_id]

Requires the API running (see README). This posts several entries to each of
the five memory types via POST /memories, waits for the vector namespaces to
settle, then prints a list of suggested questions to try against POST /chat —
each aimed at a specific memory type, so you can watch the router pick it.

Memories are project-scoped (Phase 9 enhancement), so every seeded entry is
tagged with `project_id` (default 1) pass a second argument to seed a
different project, e.g. `python3 demo/seed_phase6.py http://localhost:8010 3`.

Unlike demo_phase6.py (which asserts routing automatically), this script just
sets the stage for hands-on testing in Swagger UI or curl.
"""

import sys
import time

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"
PROJECT_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 6 # Default project_id for seeding is 1

# A handful of clearly-typed, made-up entries per memory type. Made-up so any
# correct answer proves retrieval, not the model's prior knowledge.
SEED = {
    "document": [
        {"content": "The office WiFi network is 'Halden-Guest' and its password rotates every Monday at 9am.", "source_ref": "wiki/wifi"},
        {"content": "Expense policy: meals are reimbursed up to 40 marks per day; receipts required above 10 marks.", "source_ref": "wiki/expenses"},
        {"content": "The support desk is open 09:00-18:00 on weekdays and is reachable at desk@halden.example.", "source_ref": "wiki/support"},
    ],
    "code": [
        {"content": "slugify(title): lowercases the title, replaces spaces with hyphens, and strips punctuation.", "source_ref": "utils/text.py"},
        {"content": "The RetryClient wrapper retries failed HTTP calls 3 times with exponential backoff before raising.", "source_ref": "utils/http.py"},
        {"content": "parse_duration(s) accepts strings like '2h30m' and returns the total number of seconds as an int.", "source_ref": "utils/time.py"},
    ],
    "decision": [
        {"content": "We chose PostgreSQL over MongoDB because our data is highly relational and we need transactions. Alternative considered: MongoDB. Tradeoff: less schema flexibility.", "source_ref": "adr/0003-postgres"},
        {"content": "We adopted JWT auth instead of server-side sessions to stay stateless and scale horizontally. Tradeoff: must manage token refresh.", "source_ref": "adr/0007-jwt"},
        {"content": "We picked Pinecone over a self-hosted vector DB to avoid ops overhead on the free tier. Tradeoff: vendor lock-in.", "source_ref": "adr/0011-pinecone"},
    ],
    "workflow": [
        {"content": "Deploy the backend: run tests, build the Docker image, push to the registry, deploy to staging, verify /health, then promote to production.", "source_ref": "runbooks/deploy"},
        {"content": "Release the mobile app: bump the version, run the test suite, upload the build to TestFlight, then submit for App Store review.", "source_ref": "runbooks/mobile-release"},
        {"content": "Onboard a new hire: create their email, add them to the wiki and Slack, ship a laptop, then schedule a week-one buddy session.", "source_ref": "runbooks/onboarding"},
    ],
    "conversation": [
        {"content": "In the Q2 planning call, the team agreed to pause the mobile app and focus entirely on RAG search until it ships.", "source_ref": "meeting/q2-planning"},
        {"content": "In the retro, the team agreed to stop Friday deploys after two weekend incidents.", "source_ref": "meeting/retro-2024-05"},
        {"content": "During the architecture sync, Priya flagged rising embedding costs; the group decided to cache embeddings for repeated documents.", "source_ref": "meeting/arch-sync"},
    ],
}

# Questions you can paste into POST /chat to watch the router choose each type.
SUGGESTED_QUESTIONS = {
    "decision": "Why did we choose PostgreSQL over MongoDB?",
    "workflow": "What are the steps to deploy the backend?",
    "code": "What does the slugify function do?",
    "document": "What is the office WiFi network name?",
    "conversation": "What did the team agree about Friday deploys in the retro?",
}


def main() -> None:
    total = 0
    print(f"Seeding memories across all five types (project_id={PROJECT_ID})...")
    for memory_type, entries in SEED.items():
        for entry in entries:
            r = requests.post(
                f"{BASE_URL}/memories",
                json={"memory_type": memory_type, "project_id": PROJECT_ID, **entry},
            )
            r.raise_for_status()
            total += 1
        print(f"  [{memory_type}] seeded {len(entries)} entries")
    print(f"\nSeeded {total} memories.")

    print("\nWaiting for all five vector namespaces to settle...")
    for _ in range(18):
        ready = []
        for memory_type in SEED:
            r = requests.post(
                f"{BASE_URL}/memories/search",
                json={"memory_type": memory_type, "query": "x", "top_k": 1, "project_id": PROJECT_ID},
            )
            ready.append(bool(r.ok and r.json()["results"]))
        if all(ready):
            print("All namespaces settled ready to test.\n")
            break
        time.sleep(5)
    else:
        print("Proceeding (some namespaces may still be settling).\n")

    print("=" * 72)
    print("Now try these against POST /chat and watch the 'memory_types' field:")
    print("=" * 72)
    for expected_type, question in SUGGESTED_QUESTIONS.items():
        print(f"\n  expect -> {expected_type}")
        print(f"  question: {question}")
        print(f'  curl: curl -s -X POST {BASE_URL}/chat -H "Content-Type: application/json" \\')
        print(f'           -d \'{{"project_id": {PROJECT_ID}, "message": "{question}"}}\'')

    print("\nTip: to see the router's choice, look at \"memory_types\" in each response.")
    print("Or state a NEW fact (e.g. \"We decided to adopt trunk-based development.\")")
    print("and check the \"memory_update\" field the graph should save it.")


if __name__ == "__main__":
    main()
