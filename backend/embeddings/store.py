import os
import time
import uuid

from pinecone import Pinecone, ServerlessSpec

INDEX_NAME = "memoryrag"
DIMENSION = 384  # must match BAAI/bge-small-en-v1.5's output size
NAMESPACE = "documents"

_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def ensure_index_exists() -> None:
    existing_names = [index["name"] for index in _pc.list_indexes()]
    if INDEX_NAME in existing_names:
        return

    _pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    while not _pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(1)


def _get_index():
    return _pc.Index(INDEX_NAME)


def add_chunks(chunks: list[str], embeddings: list[list[float]], project_id: int, source_filename: str) -> int:
    vectors = [
        {
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {"project_id": project_id, "source_filename": source_filename, "chunk_text": chunk},
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    _get_index().upsert(vectors=vectors, namespace=NAMESPACE)
    return len(vectors)


def search(query_embedding: list[float], top_k: int, project_id: int | None = None) -> list[dict]:
    # When project_id is given, Pinecone only compares against vectors whose
    # metadata matches — so one project's chat can't retrieve another's docs.
    query_filter = {"project_id": project_id} if project_id is not None else None
    result = _get_index().query(
        vector=query_embedding,
        top_k=top_k,
        namespace=NAMESPACE,
        include_metadata=True,
        filter=query_filter,
    )
    return [
        {
            "text": match["metadata"]["chunk_text"],
            "score": match["score"],
            "metadata": {
                "project_id": match["metadata"]["project_id"],
                "source_filename": match["metadata"]["source_filename"],
            },
        }
        for match in result["matches"]
    ]
