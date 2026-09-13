"""
Admin-only document management. Regular users can only list/view documents
(read access), never upload — enforced via require_admin, not by hiding
the button on the frontend (that's not real security).
"""
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from bson import ObjectId

from app.core.deps import require_admin, get_current_user
from app.core.config import settings
from app.db.mongodb import documents_collection
from app.models.document import DocumentOut
from app.services.pdf_service import extract_text_from_pdf, validate_pdf
from app.core.limiter import limiter
from app.services.ingestion_service import ingest_document
from app.db.mongodb import chunks_collection

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentOut)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    safe_name = f"{uuid.uuid4().hex}.pdf"
    save_path = UPLOAD_DIR / safe_name

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        validate_pdf(str(save_path))
        text, page_count = extract_text_from_pdf(str(save_path))
    except ValueError as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    if not text.strip():
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="No extractable text found (likely a scanned/image PDF)")

    doc = {
        "filename": file.filename,
        "stored_path": str(save_path),
        "uploaded_by": str(admin["_id"]),
        "uploaded_at": datetime.now(timezone.utc),
        "page_count": page_count,
        "char_count": len(text),
        "extracted_text": text,   # Milestone 3 will chunk this
        "status": "processing",  # flips to "ready" once Milestone 3 embeds + indexes it
    }
    result = await documents_collection.insert_one(doc)
    document_id = str(result.inserted_id)

    # Chunk + embed + index right away. For a fresher-scale project keeping
    # this synchronous is fine and easier to reason about/demo; move to a
    # background task later if upload volume grows.
    chunk_count = await ingest_document(document_id, text)

    # Re-fetch to get the final status ("ready" or "failed") set by ingestion
    final_doc = await documents_collection.find_one({"_id": result.inserted_id})

    return DocumentOut(
        id=document_id,
        filename=final_doc["filename"],
        uploaded_by=final_doc["uploaded_by"],
        uploaded_at=final_doc["uploaded_at"],
        page_count=final_doc["page_count"],
        char_count=final_doc["char_count"],
        status=final_doc["status"],
    )


@router.get("/", response_model=list[DocumentOut])
async def list_documents(user: dict = Depends(get_current_user)):
    """Any authenticated user can see what documents exist — needed so they
    know what they're allowed to ask questions about."""
    docs = []
    async for d in documents_collection.find():
        docs.append(DocumentOut(
            id=str(d["_id"]),
            filename=d["filename"],
            uploaded_by=d["uploaded_by"],
            uploaded_at=d["uploaded_at"],
            page_count=d["page_count"],
            char_count=d["char_count"],
            status=d["status"],
        ))
    return docs


@router.delete("/{document_id}")
async def delete_document(document_id: str, admin: dict = Depends(require_admin)):
    doc = await documents_collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    Path(doc["stored_path"]).unlink(missing_ok=True)
    await documents_collection.delete_one({"_id": ObjectId(document_id)})
    await chunks_collection.delete_many({"document_id": document_id})
    return {"detail": "Document deleted"}