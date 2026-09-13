"""
Splits document text into overlapping chunks for embedding.

Why overlap matters: if a sentence answering the user's question straddles
the boundary between chunk N and chunk N+1, a naive non-overlapping split
means NEITHER chunk contains the full answer. The overlap acts as a safety
margin so context isn't lost at boundaries.

Note on "tokens": we approximate 1 token ≈ 1 word here for simplicity.
This is intentionally rough — good enough for consistent chunk sizing.
If you later swap in a real tokenizer (e.g. tiktoken), the chunk_size
config value stays meaningful either way.
"""
from app.core.config import settings


def chunk_text(
    text: str,
    chunk_size_tokens: int = None,
    overlap_tokens: int = None,
) -> list[str]:
    chunk_size_tokens = chunk_size_tokens or settings.chunk_size_tokens
    overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens

    if overlap_tokens >= chunk_size_tokens:
        raise ValueError("overlap_tokens must be smaller than chunk_size_tokens")

    words = text.split()
    if not words:
        return []

    step = chunk_size_tokens - overlap_tokens
    chunks = []

    start = 0
    while start < len(words):
        end = start + chunk_size_tokens
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words).strip()
        if chunk_str:
            chunks.append(chunk_str)
        if end >= len(words):
            break
        start += step

    return chunks