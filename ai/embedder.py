"""
Embedder — generates semantic vector embeddings using nomic-embed-text.
Used for similarity scoring between job descriptions and profile text.
"""

import logging
import math
from typing import Optional

from ai.client import ollama_client
from config.settings import settings

logger = logging.getLogger(__name__)


def embed_text(text: str) -> Optional[list[float]]:
    """
    Generate an embedding vector for a piece of text.
    Returns None if Ollama is unavailable or the model fails.
    """
    if not text or not text.strip():
        return None
    try:
        return ollama_client.embed(
            model=settings.model_embedder,
            text=text[:4000],  # cap to avoid token overflow
        )
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value between -1.0 and 1.0 (1.0 = identical).
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Compute semantic similarity between two texts using embeddings.
    Returns 0.0–1.0. Falls back to 0.0 if embeddings fail.
    """
    vec_a = embed_text(text_a)
    vec_b = embed_text(text_b)

    if not vec_a or not vec_b:
        return 0.0

    raw = cosine_similarity(vec_a, vec_b)
    # Normalise from [-1, 1] to [0, 1]
    return (raw + 1) / 2
