"""
Wraps SentenceTransformers so the rest of the app never touches the model
directly. Loaded once as a module-level singleton since loading the model
from disk/HF cache takes real time and we don't want to repeat it per
request.
"""
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Returns L2-normalized float32 embeddings, shape (len(texts), dim).
    Normalizing here means a plain inner product in FAISS is equivalent
    to cosine similarity, which is why the vector store uses IndexFlatIP.
    """
    model = get_model()
    embeddings = model.encode(
        texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    return embeddings.astype("float32")


def embed_query(query: str) -> np.ndarray:
    return embed_texts([query])[0]
