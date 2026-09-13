"""
Isolated PDF -> text logic. Kept out of the route handler so it can be
unit-tested on its own, and reused later (e.g. a re-processing endpoint).
"""
import pdfplumber
from pathlib import Path


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """
    Returns (full_text, page_count).
    Pages are joined with a page marker so later chunking can still tell
    which page a chunk came from, if we want that later.
    """
    full_text_parts = []
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            full_text_parts.append(f"\n\n[PAGE {i + 1}]\n{text}")

    full_text = "".join(full_text_parts).strip()
    return full_text, page_count


def validate_pdf(file_path: str, max_size_mb: int = 20) -> None:
    """Basic guardrails before we bother extracting anything."""
    path = Path(file_path)
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f"File too large: {size_mb:.1f}MB (max {max_size_mb}MB)")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")