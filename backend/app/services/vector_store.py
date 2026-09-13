"""
Manages the FAISS index as a module-level singleton, loaded from disk on
first use and persisted after every write.

Why a separate id_map: FAISS only knows integer positions (0, 1, 2, ...)
— it has no concept of "this vector belongs to chunk X of document Y".
We keep a parallel list, id_map, where id_map[i] = the MongoDB chunk _id
for the vector at FAISS position i. This mapping is the piece that lets
a FAISS search result turn back into actual readable text.

Known limitation (flagged honestly, not hidden): this uses a single
in-process index with no file locking. Fine for one server process /
personal project. If you ever run multiple backend workers, they'd each
have their own copy of the index in memory — a real vector DB (or a
lock/queue around writes) would be the fix at that scale.
"""
import json
import threading
from pathlib import Path

import faiss
import numpy as np

from app.core.config import settings

_index: faiss.Index | None = None
_id_map: list[str] = []
_lock = threading.Lock()

EMBEDDING_DIM = 768  # must match embedding_service's model output dim

INDEX_DIR = Path(settings.vector_index_dir)
INDEX_PATH = INDEX_DIR / "faiss.index"
ID_MAP_PATH = INDEX_DIR / "id_map.json"


def _ensure_loaded():
    global _index, _id_map
    if _index is not None:
        return

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if INDEX_PATH.exists() and ID_MAP_PATH.exists():
        _index = faiss.read_index(str(INDEX_PATH))
        _id_map = json.loads(ID_MAP_PATH.read_text())
    else:
        _index = faiss.IndexFlatIP(EMBEDDING_DIM)  # inner product == cosine, since vectors are normalized
        _id_map = []


def _persist():
    faiss.write_index(_index, str(INDEX_PATH))
    ID_MAP_PATH.write_text(json.dumps(_id_map))


def add_vectors(embeddings: np.ndarray, chunk_ids: list[str]) -> None:
    """embeddings: (n, EMBEDDING_DIM) float32, already normalized. chunk_ids
    must be the same length and in the same order as embeddings' rows."""
    if len(embeddings) != len(chunk_ids):
        raise ValueError("embeddings and chunk_ids must be the same length")
    if len(embeddings) == 0:
        return

    with _lock:
        _ensure_loaded()
        _index.add(embeddings)
        _id_map.extend(chunk_ids)
        _persist()


def search(query_embedding: np.ndarray, top_k: int = None) -> list[tuple[str, float]]:
    """Returns a list of (chunk_id, similarity_score) tuples, best first."""
    top_k = top_k or settings.top_k_chunks

    with _lock:
        _ensure_loaded()
        if _index.ntotal == 0:
            return []

        k = min(top_k, _index.ntotal)
        query_vec = query_embedding.reshape(1, -1).astype("float32")
        scores, indices = _index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((_id_map[idx], float(score)))
        return results


def total_vectors() -> int:
    with _lock:
        _ensure_loaded()
        return _index.ntotal


def reset_index_for_testing() -> None:
    """Only for tests — wipes the in-memory index without touching disk."""
    global _index, _id_map
    _index = None
    _id_map = []