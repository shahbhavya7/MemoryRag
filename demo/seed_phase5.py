"""Seeds each of the five memory types with a few example entries.

Usage:
    python3 demo/seed_phase5.py [base_url]

Requires the API to be running (see README). Each entry is posted to
POST /memories, which embeds it into the matching Pinecone namespace and
logs it in Postgres. All content is deliberately made-up so it's obvious
which type any given entry belongs to.
"""

import sys

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# 2-3 example entries per memory type.
SEED_ENTRIES = {
    "document": [
        {"content": "The Halden Onboarding Guide explains how new hires request laptop access and join the internal wiki.", "source_ref": "wiki/onboarding"},
        {"content": "Company travel policy: flights under 4 hours are booked economy; hotels are capped at 180 marks per night.", "source_ref": "wiki/travel-policy"},
    ],
    "code": [
        {"content": "def normalize_email(email: str) -> str: return email.strip().lower()", "source_ref": "backend/utils/email.py"},
        {"content": "class RateLimiter: allows N requests per window and raises TooManyRequests when exceeded.", "source_ref": "backend/middleware/rate_limit.py"},
    ],
    "decision": [
        {"content": "Decision: adopt JWT auth instead of server-side sessions. Reason: avoid storing session state; enables stateless horizontal scaling. Tradeoff: must handle refresh tokens.", "source_ref": "adr/0007-jwt-auth"},
        {"content": "Decision: use Pinecone serverless over a self-hosted vector DB. Reason: zero ops for a student project; free tier is sufficient. Tradeoff: vendor lock-in and eventual consistency.", "source_ref": "adr/0011-pinecone"},
    ],
    "workflow": [
        {"content": "Deploy backend: run tests -> build Docker image -> push image to registry -> deploy to staging -> verify /health -> promote to production.", "source_ref": "runbooks/deploy"},
        {"content": "Incident response: acknowledge alert -> open incident channel -> identify blast radius -> mitigate -> write postmortem within 48 hours.", "source_ref": "runbooks/incident"},
    ],
    "conversation": [
        {"content": "In the Q2 planning call, the team agreed to pause the mobile app and focus all effort on the RAG search feature until it ships.", "source_ref": "meeting/q2-planning"},
        {"content": "During the architecture sync, Priya raised that embedding costs could spike; the group decided to cache embeddings for repeated documents.", "source_ref": "meeting/arch-sync"},
    ],
}


def main() -> None:
    total = 0
    for memory_type, entries in SEED_ENTRIES.items():
        for entry in entries:
            response = requests.post(
                f"{BASE_URL}/memories",
                json={"memory_type": memory_type, **entry},
            )
            response.raise_for_status()
            body = response.json()
            print(f"[{memory_type}] seeded id={body['id']}: {body['content'][:60]}...")
            total += 1
    print(f"\nSeeded {total} memories across {len(SEED_ENTRIES)} memory types.")


if __name__ == "__main__":
    main()
