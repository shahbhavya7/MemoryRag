"""Walks the Phase 4 basic-RAG chat flow against a running MemoryRAG API.

Usage:
    python3 demo/demo_phase4.py [base_url]

Requires the API to already be running (see README) with a working
PINECONE_API_KEY *and* LLM_PROVIDER + LLM_API_KEY set.

The point of this demo is to make *grounding* visible: we upload a short
made-up document, ask questions about it, and print both the LLM's answer
AND the exact source chunks it was given — so you can see the answer came
from the retrieved context, not from the model's imagination. The last
question deliberately asks about something NOT in the document, so you can
see the model decline to answer rather than hallucinate.
"""

import sys
import time
import uuid

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# A unique project id per run so repeated runs don't retrieve each other's docs.
PROJECT_ID = int(uuid.uuid4().int % 1_000_000)

DOCUMENT_TEXT = """
The Aurora Tram is a fictional cable car that runs up Mount Veyra in the
made-up town of Halden. It departs every 20 minutes from the base station
and takes exactly 12 minutes to reach the summit. Each tram car is painted
pale violet and can carry up to 18 passengers at a time.

Tickets for the Aurora Tram cost 7 silver marks for adults and 3 silver
marks for children under twelve. The tram does not run during thunderstorms,
because the exposed upper track above the treeline is considered unsafe when
there is lightning nearby.
"""

GROUNDED_QUESTIONS = [
    "How long does the Aurora Tram take to reach the summit?",
    "Why doesn't the tram run during thunderstorms?",
]

# This is NOT covered by the document — a well-behaved grounded system should
# say it doesn't know, rather than inventing an answer.
OUT_OF_SCOPE_QUESTION = "Who invented the Aurora Tram and in what year?"


def show(label: str, response: requests.Response) -> None:
    print(f"\n--- {label} ---")
    print(f"{response.request.method} {response.request.url} -> {response.status_code}")
    if response.content:
        print(response.json())


def ask(question: str) -> None:
    result = requests.post(
        f"{BASE_URL}/chat",
        json={"project_id": PROJECT_ID, "message": question},
    )
    print(f"\n================ Q: {question} ================")
    print(f"POST {result.request.url} -> {result.status_code}")
    result.raise_for_status()
    body = result.json()
    print(f"\nANSWER:\n{body['answer']}")
    print("\nSOURCES THE ANSWER WAS GROUNDED IN:")
    if not body["sources"]:
        print("  (none retrieved)")
    for i, src in enumerate(body["sources"], 1):
        snippet = src["text"][:160].replace("\n", " ")
        print(f"  [{i}] score={src['score']:.3f} from {src['source_filename']}: {snippet}...")


def main() -> None:
    uploaded = requests.post(
        f"{BASE_URL}/documents/upload",
        data={"project_id": PROJECT_ID, "text": DOCUMENT_TEXT},
    )
    show(f"Upload Aurora Tram document (project_id={PROJECT_ID})", uploaded)
    uploaded.raise_for_status()

    # Give Pinecone's serverless index a moment to make the new vectors
    # searchable (same eventual-consistency reason as the Phase 3 demo).
    print("\nWaiting a few seconds for the vector index to settle...")
    time.sleep(8)

    for question in GROUNDED_QUESTIONS:
        ask(question)

    print("\n\n### Now an out-of-scope question the document CANNOT answer ###")
    ask(OUT_OF_SCOPE_QUESTION)

    print(
        "\n\nDone. Notice the first two answers match the source chunks shown, "
        "while the last one is declined rather than made up — that's grounding working."
    )


if __name__ == "__main__":
    main()
