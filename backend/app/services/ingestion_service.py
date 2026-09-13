"""
Orchestrates the full ingest pipeline for one document: chunk the text,
save each chunk's text in MongoDB (source of truth for what a chunk says),
embed the chunks, and add the vectors to FAISS (source of truth for
similarity search). The two stores are linked by chunk_id.

This is called right after upload. For a bigger document library you'd
push this onto a background task queue instead of running it inline in
the request — flagged in the roadmap, not needed yet at this scale.
"""
from bson import ObjectId

from app.db.mongodb import chunks_collection, documents_collection
from app.services.chunking_service import chunk_text
from app.services.embedding_service import embed_texts
from app.services import vector_store


async def ingest_document(document_id: str, full_text: str) -> int:
    """Returns the number of chunks created."""
    chunks = chunk_text(full_text)
    if not chunks:
        await documents_collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"status": "failed"}},
        )
        return 0

    # 1. Insert chunk documents first so we have real Mongo _ids to pair with vectors
    chunk_docs = [
        {"document_id": document_id, "chunk_index": i, "text": chunk}
        for i, chunk in enumerate(chunks)
    ]
    result = await chunks_collection.insert_many(chunk_docs)
    chunk_ids = [str(cid) for cid in result.inserted_ids]

    # 2. Embed all chunks in one batch call (much faster than one-by-one)
    embeddings = embed_texts(chunks)

    # 3. Add to FAISS, keyed by the same chunk_ids
    vector_store.add_vectors(embeddings, chunk_ids)

    # 4. Flip the document to "ready" — this is what the frontend/query
    # endpoint should check before letting a user query it
    await documents_collection.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": "ready"}},
    )

    return len(chunks)