"""
The core RAG loop: embed the question, retrieve the most relevant chunks
via FAISS, look up their text + source document in MongoDB, ask Gemini to
answer using only that context, and log the exchange to chat history.

Any authenticated user can query — this is read-only over documents that
are already public within the app (upload is what's admin-gated, not
reading).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from bson import ObjectId

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.mongodb import chunks_collection, documents_collection, chat_history_collection
from app.models.chat import QueryRequest, QueryResponse, SourceChunk, ChatHistoryOut
from app.services.embedding_service import embed_query
from app.services import vector_store
from app.services.gemini_service import generate_answer
from app.core.limiter import limiter

logger = logging.getLogger("documind")

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
async def query_documents(
    request: Request,
    payload: QueryRequest,
    user: dict = Depends(get_current_user),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # 1. Embed the question and search FAISS for the closest chunks.
    # When scoping to one document, over-fetch candidates (FAISS has no
    # native filter-by-metadata) then filter down to that document below —
    # otherwise a document-scoped question could come back empty just
    # because the top-k globally happened to all be from OTHER documents.
    query_vec = embed_query(payload.question)
    fetch_k = settings.top_k_chunks * 5 if payload.document_id else settings.top_k_chunks
    search_results = vector_store.search(query_vec, top_k=fetch_k)  # [(chunk_id, score), ...]

    if not search_results:
        answer = "I don't have enough information in the uploaded documents to answer that."
        await _log_chat(user, payload.question, answer)
        return QueryResponse(answer=answer, sources=[])

    # 2. Fetch the actual chunk text + which document each came from
    chunk_ids = [ObjectId(cid) for cid, _ in search_results]

    chunks_cursor = chunks_collection.find({"_id": {"$in": chunk_ids}})
    chunks_by_id = {}
    async for c in chunks_cursor:
        chunks_by_id[str(c["_id"])] = c

    # Resolve document filenames for citation display (one lookup per unique doc)
    doc_ids = {c["document_id"] for c in chunks_by_id.values()}
    doc_id_objs = [ObjectId(d) for d in doc_ids]
    docs_cursor = documents_collection.find({"_id": {"$in": doc_id_objs}})
    filename_by_doc_id = {}
    async for d in docs_cursor:
        filename_by_doc_id[str(d["_id"])] = d["filename"]

    # 3. Build the ordered context (best match first) and source list.
    # If a document filter was requested, drop chunks from other documents
    # here, then cap back down to the normal top_k so Gemini still only
    # sees a focused, relevant context window.
    context_texts = []
    sources = []
    for cid, score in search_results:
        if len(sources) >= settings.top_k_chunks:
            break
        chunk = chunks_by_id.get(cid)
        if not chunk:
            continue
        if payload.document_id and chunk["document_id"] != payload.document_id:
            continue
        context_texts.append(chunk["text"])
        sources.append(SourceChunk(
            chunk_id=cid,
            document_id=chunk["document_id"],
            filename=filename_by_doc_id.get(chunk["document_id"], "unknown"),
            text=chunk["text"],
            score=score,
        ))

    if payload.document_id and not sources:
        answer = "I couldn't find relevant information in the selected document to answer that."
        await _log_chat(user, payload.question, answer)
        return QueryResponse(answer=answer, sources=[])

    # 4. Ask Gemini, grounded strictly in the retrieved context
    try:
        answer = generate_answer(payload.question, context_texts)
    except Exception as e:
        logger.error(f"Gemini call failed for question '{payload.question}': {e}")
        answer = "The AI service is temporarily unavailable. Please try again shortly."

    await _log_chat(user, payload.question, answer)

    return QueryResponse(answer=answer, sources=sources)


@router.get("/query/history", response_model=list[ChatHistoryOut])
async def get_chat_history(user: dict = Depends(get_current_user)):
    history = []
    cursor = chat_history_collection.find({"user_id": str(user["_id"])}).sort("asked_at", -1)
    async for h in cursor:
        history.append(ChatHistoryOut(
            id=str(h["_id"]),
            question=h["question"],
            answer=h["answer"],
            asked_at=h["asked_at"],
        ))
    return history


async def _log_chat(user: dict, question: str, answer: str) -> None:
    await chat_history_collection.insert_one({
        "user_id": str(user["_id"]),
        "question": question,
        "answer": answer,
        "asked_at": datetime.now(timezone.utc),
    })