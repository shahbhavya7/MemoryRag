"""Walks the Phase 3 embeddings + vector search lifecycle against a running MemoryRAG API.

Usage:
    python3 demo/demo_phase3.py [base_url]

Requires the API to already be running (see README: uvicorn backend.main:app),
with PINECONE_API_KEY set and a free Pinecone account available.
The first request that touches embeddings will download the BAAI/bge-small-en-v1.5
model (~130MB) from Hugging Face, so it may take a little longer than later runs.

Scores here are Pinecone's cosine similarity: higher means more similar
(the opposite convention from a "distance," where lower would mean closer).
"""

import sys
import time

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# A made-up topic ("Glimmerwood squirrels") so we can be sure any correct
# search result came from semantic understanding, not from prior knowledge
# the embedding model already had about a real-world subject.
DOCUMENT_TEXT = """
Glimmerwood squirrels are a fictional species said to live in the misty
pine forests of the made-up region of Aldervale. Unlike ordinary squirrels,
Glimmerwood squirrels have faintly bioluminescent tails that glow a soft
blue-green color in the dark, which they use to signal to each other across
long distances at night. Local folklore claims the glow grows brighter when
the squirrel is nervous or excited.

Glimmerwood squirrels build their nests, called driftnests, out of moss and
spider silk rather than twigs, which lets the nests sway gently in the wind
without falling apart. A driftnest is usually woven near the very top of the
tallest pine tree in a squirrel's territory, both for safety from predators
and because the height helps their tail-glow signals travel further.

During the autumn, Glimmerwood squirrels gather a rare blue acorn that only
grows on Aldervale pines. They store these blue acorns in a separate part of
their driftnest from ordinary acorns, because blue acorns are saved
specifically for a midwinter feast the squirrels hold once a year, when
groups from different driftnests gather in a single clearing to eat
together and exchange tail-glow greetings.
"""

# A second, unrelated made-up topic. With only one document in the store,
# every search would trivially "win" — this distractor lets us prove the
# search actually ranks the relevant chunk above an irrelevant one, instead
# of just returning whatever happens to exist.
DISTRACTOR_TEXT = """
The Sunspire Kite Tournament is a fictional yearly competition held in the
made-up desert town of Cindervale. Competitors build kites out of dyed silk
and thin bamboo rods, then race them along a fixed canyon course while
judges score style points for sharp turns near the canyon walls. The
tournament's grand prize is a hand-painted ceramic sun medallion, awarded
each year to whichever team completes the course fastest without their kite
touching the canyon floor.
"""

QUERIES = [
    "What color do Glimmerwood squirrel tails glow?",
    # A paraphrase, not a quote — no shared keywords with "driftnest" or
    # "moss and spider silk" in the source text, so a keyword search would
    # likely miss it, but a semantic search should still find it.
    "How do these squirrels build their homes without using twigs?",
    "What special food do they eat once a year in winter?",
]


def show(label: str, response: requests.Response) -> None:
    print(f"\n--- {label} ---")
    print(f"{response.request.method} {response.request.url} -> {response.status_code}")
    if response.content:
        print(response.json())


def wait_for_index_to_settle(max_wait_seconds: int = 60, poll_interval_seconds: int = 5) -> None:
    # Pinecone serverless is eventually consistent: right after the very
    # first upserts into a fresh namespace, similarity ranking can be
    # temporarily wrong (not just "missing" the new vectors, but genuinely
    # mis-ordered) until the index finishes settling — this has been
    # observed taking up to about a minute. A fixed short sleep isn't
    # reliable, so instead we poll a known query until its expected top
    # match shows up, and give up gracefully if it takes unusually long.
    print("\nWaiting for the Pinecone index to settle after the fresh upserts...")
    canary_query = QUERIES[0]
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        result = requests.post(f"{BASE_URL}/documents/search", json={"query": canary_query, "top_k": 1})
        result.raise_for_status()
        top_project = result.json()["results"][0]["metadata"]["project_id"]
        if top_project == 1:
            print("Index looks settled — proceeding with the real queries.")
            return
        time.sleep(poll_interval_seconds)

    print(f"Index didn't settle within {max_wait_seconds}s — proceeding anyway; results below may be affected.")


def main() -> None:
    uploaded = requests.post(
        f"{BASE_URL}/documents/upload",
        data={"project_id": 1, "text": DOCUMENT_TEXT},
    )
    show("Upload document about Glimmerwood squirrels", uploaded)
    uploaded.raise_for_status()

    uploaded_distractor = requests.post(
        f"{BASE_URL}/documents/upload",
        data={"project_id": 2, "text": DISTRACTOR_TEXT},
    )
    show("Upload unrelated distractor document (kite tournament)", uploaded_distractor)
    uploaded_distractor.raise_for_status()

    wait_for_index_to_settle()

    for query in QUERIES:
        result = requests.post(
            f"{BASE_URL}/documents/search",
            json={"query": query, "top_k": 2},
        )
        show(f"Search: {query!r}", result)
        result.raise_for_status()

        top_source = result.json()["results"][0]["metadata"]["source_filename"]
        top_project = result.json()["results"][0]["metadata"]["project_id"]
        assert top_project == 1, (
            f"Expected the squirrel document (project_id=1) to rank first, "
            f"got project_id={top_project} ({top_source})"
        )

    print(
        "\nAll Phase 3 embedding + semantic search checks completed successfully — "
        "every query correctly ranked the relevant squirrel chunk above the unrelated kite-tournament chunk."
    )


if __name__ == "__main__":
    main()
