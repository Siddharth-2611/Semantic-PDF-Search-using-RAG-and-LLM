"""
FAISS vector index management.

Design decisions worth knowing for an interview:

- Single global index, not one-per-user. Each vector is stored under a
  stable integer id (Chunk.vector_id) via IndexIDMap, so per-user
  isolation is enforced at the SQL layer (Chunk -> Document -> owner_id)
  rather than by maintaining N separate FAISS indexes. This scales better
  as user count grows and keeps FAISS itself simple.

- IndexFlatIP (inner product) instead of IndexFlatL2. Embeddings are
  L2-normalized in embeddings.py, so inner product is mathematically
  equivalent to cosine similarity, but avoids computing a square root
  per comparison. For a corpus this size, exact (Flat) search is fast
  enough that we don't need an approximate index like IVF/HNSW.

- The index is persisted to disk after every write so it survives
  restarts without re-embedding every document.
"""
import os
import threading

import faiss
import numpy as np

from app.config import settings

_lock = threading.RLock()
_index: faiss.Index | None = None

INDEX_PATH = os.path.join(settings.faiss_index_dir, "index.faiss")


def _load_or_create() -> faiss.Index:
    os.makedirs(settings.faiss_index_dir, exist_ok=True)
    if os.path.exists(INDEX_PATH):
        return faiss.read_index(INDEX_PATH)
    flat = faiss.IndexFlatIP(settings.embedding_dim)
    return faiss.IndexIDMap(flat)


def get_index() -> faiss.Index:
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                _index = _load_or_create()
    return _index


def _persist():
    faiss.write_index(_index, INDEX_PATH)


def add_vectors(vector_ids: list[int], vectors: np.ndarray):
    with _lock:
        index = get_index()
        ids = np.array(vector_ids, dtype="int64")
        index.add_with_ids(vectors, ids)
        _persist()


def remove_vectors(vector_ids: list[int]):
    with _lock:
        index = get_index()
        ids = np.array(vector_ids, dtype="int64")
        index.remove_ids(ids)
        _persist()


def search(query_vector: np.ndarray, top_k: int) -> tuple[list[int], list[float]]:
    """Returns (vector_ids, scores) sorted by descending similarity."""
    with _lock:
        index = get_index()
        if index.ntotal == 0:
            return [], []
        scores, ids = index.search(query_vector.reshape(1, -1), top_k)
    valid = [(i, s) for i, s in zip(ids[0], scores[0]) if i != -1]
    if not valid:
        return [], []
    ids_out, scores_out = zip(*valid)
    return [int(i) for i in ids_out], [float(s) for s in scores_out]
