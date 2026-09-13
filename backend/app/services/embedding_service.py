"""
Wraps the embedding model as a lazy-loaded singleton — the model is ~400MB
and takes a few seconds to load, so we load it ONCE on first use and reuse
it for every request, not once per API call.

Embeddings are L2-normalized so we can use inner product (dot product) in
FAISS as a proxy for cosine similarity — this is the standard trick that
lets us use the faster IndexFlatIP instead of IndexFlatL2 with a separate
normalization step at search time.
"""
import numpy as np
from app.core.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        # Imported here (not at module top) so the ~400MB model download/load
        # only happens the first time embeddings are actually needed, not on
        # every app startup (e.g. during tests or when just hitting /health).
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model_name)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Returns a (n_texts, embedding_dim) float32 array, L2-normalized.
    """
    if not texts:
        return np.zeros((0, 768), dtype="float32")  # bge-base-en-v1.5 dim = 768

    model = _get_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,   # <-- makes inner product == cosine similarity
        show_progress_bar=False,
    )
    return embeddings.astype("float32")


def embed_query(query: str) -> np.ndarray:
    """Convenience wrapper for embedding a single query string at search time."""
    return embed_texts([query])[0]