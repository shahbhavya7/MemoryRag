def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    # Word count is used as a simple stand-in for token count, so this stays
    # dependency-light — good enough for chunking, not an exact token budget.
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks
