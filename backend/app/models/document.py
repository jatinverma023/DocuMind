from pydantic import BaseModel
from datetime import datetime


class DocumentOut(BaseModel):
    id: str
    filename: str
    uploaded_by: str
    uploaded_at: datetime
    page_count: int
    char_count: int
    status: str  # "processing" | "ready" | "failed" — flips to "ready" once Milestone 3 embeds it