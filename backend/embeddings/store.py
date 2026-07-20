import os
import time
import uuid

from pinecone import Pinecone, ServerlessSpec

INDEX_NAME = "memoryrag"
DIMENSION = 384  # must match BAAI/bge-small-en-v1.5's output size

# Phase 5: instead of one "documents" namespace, we keep five memory-type
# namespaces inside the SAME index. Namespaces isolate vectors from each other
# for free (no extra index needed, which matters on Pinecone's free tier).
MEMORY_NAMESPACES = {
    "document": "document_memory",
    "code": "code_memory",
    "decision": "decision_memory",
    "workflow": "workflow_memory",
    "conversation": "conversation_memory",
}

# Uploaded documents (Phase 3/4) live in the document-memory namespace.
DOCUMENT_NAMESPACE = MEMORY_NAMESPACES["document"]

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


# --- Document chunks (Phase 3/4) -------------------------------------------

def add_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    project_id: int,
    source_filename: str,
    namespace: str = DOCUMENT_NAMESPACE,
) -> int:
    vectors = [
        {
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {"project_id": project_id, "source_filename": source_filename, "chunk_text": chunk},
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    _get_index().upsert(vectors=vectors, namespace=namespace)
    return len(vectors)


def search(
    query_embedding: list[float],
    top_k: int,
    namespace: str = DOCUMENT_NAMESPACE,
    project_id: int | None = None,
) -> list[dict]:
    # When project_id is given, Pinecone only compares against vectors whose
    # metadata matches — so one project's chat can't retrieve another's docs.
    query_filter = {"project_id": project_id} if project_id is not None else None
    result = _get_index().query(
        vector=query_embedding,
        top_k=top_k,
        namespace=namespace,
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


# --- Memories (Phase 5) ----------------------------------------------------

def add_memory_vector(
    namespace: str,
    embedding: list[float],
    memory_id: int,
    memory_type: str,
    content: str,
    source_ref: str | None,
    project_id: int | None = None,
) -> str:
    # Pinecone metadata can't hold null values, so only include optional keys when set.
    metadata = {"memory_id": memory_id, "memory_type": memory_type, "content": content}
    if source_ref is not None:
        metadata["source_ref"] = source_ref
    # project_id makes memories project-scoped: retrieval filters on it so one
    # project's chat can't see another project's memories.
    if project_id is not None:
        metadata["project_id"] = project_id

    vector_id = str(uuid.uuid4())
    _get_index().upsert(
        vectors=[{"id": vector_id, "values": embedding, "metadata": metadata}],
        namespace=namespace,
    )
    return vector_id


def search_namespace(
    namespace: str,
    query_embedding: list[float],
    top_k: int,
    project_id: int | None = None,
) -> list[dict]:
    # Generic search used by the Phase 6 routing graph. A namespace can hold
    # both document chunks (metadata key "chunk_text") and memory entries
    # (key "content"), so we read whichever text key is present.
    # When project_id is given, only vectors tagged with that project match —
    # this is what makes memories project-scoped.
    query_filter = {"project_id": project_id} if project_id is not None else None
    result = _get_index().query(
        vector=query_embedding,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
        filter=query_filter,
    )
    out = []
    for match in result["matches"]:
        md = match["metadata"]
        out.append(
            {
                "text": md.get("content") or md.get("chunk_text") or "",
                "score": match["score"],
                "source_ref": md.get("source_ref") or md.get("source_filename"),
            }
        )
    return out


def search_memories(
    namespace: str,
    query_embedding: list[float],
    top_k: int,
    project_id: int | None = None,
) -> list[dict]:
    query_filter = {"project_id": project_id} if project_id is not None else None
    result = _get_index().query(
        vector=query_embedding,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
        filter=query_filter,
    )
    return [
        {
            "memory_id": match["metadata"].get("memory_id"),
            "memory_type": match["metadata"]["memory_type"],
            "content": match["metadata"]["content"],
            "source_ref": match["metadata"].get("source_ref"),
            "score": match["score"],
        }
        for match in result["matches"]
    ]
