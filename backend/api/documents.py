from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.embeddings.chunking import chunk_text
from backend.embeddings.model import embed_query, embed_texts
from backend.embeddings.store import add_chunks, search
from backend.schemas import DocumentSearchRequest, DocumentSearchResponse, DocumentSearchResult, DocumentUploadOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadOut, status_code=201)
async def upload_document(
    project_id: int = Form(...),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    if file is not None:
        raw_bytes = await file.read()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File is not valid UTF-8 text. Upload a plain .txt file, not a PDF/Word doc/binary file.",
            )
        source_filename = file.filename or "uploaded_file.txt"
    elif text is not None:
        content = text
        source_filename = "raw_text_input.txt"
    else:
        raise HTTPException(status_code=400, detail="Provide either `text` or `file`")

    chunks = chunk_text(content)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text content to embed")

    embeddings = embed_texts(chunks)
    chunks_created = add_chunks(chunks, embeddings, project_id, source_filename)
    return DocumentUploadOut(source_filename=source_filename, chunks_created=chunks_created)


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(payload: DocumentSearchRequest):
    query_embedding = embed_query(payload.query)
    results = search(query_embedding, payload.top_k)
    return DocumentSearchResponse(results=[DocumentSearchResult(**r) for r in results])
