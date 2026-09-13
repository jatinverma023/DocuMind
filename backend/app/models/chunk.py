from pydantic import BaseModel


class ChunkOut(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str