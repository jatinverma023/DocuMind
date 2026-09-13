from pydantic import BaseModel
from datetime import datetime


class QueryRequest(BaseModel):
    question: str
    document_id: str | None = None  # if set, scope retrieval to just this document


class SourceChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class ChatHistoryOut(BaseModel):
    id: str
    question: str
    answer: str
    asked_at: datetime