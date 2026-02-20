"""SBERT Embedding Service - Story 3.1"""
import time
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    """Service for encoding text into semantic embeddings using SBERT."""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load SBERT model (called once at startup)."""
        print(f"Loading SBERT model: {settings.embedding_model}")
        start = time.time()
        self._model = SentenceTransformer(settings.embedding_model)
        elapsed = time.time() - start
        print(f"SBERT model loaded in {elapsed:.2f}s")

    def encode(self, text: str) -> np.ndarray:
        """
        Encode text into a 384-dimensional embedding vector.

        Args:
            text: The text to encode

        Returns:
            numpy array of shape (384,) with float32 values
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(settings.embedding_dim, dtype=np.float32)

        start = time.time()
        embedding = self._model.encode(text, show_progress_bar=False)
        elapsed = (time.time() - start) * 1000  # ms

        if elapsed > 100:
            print(f"Warning: Encoding took {elapsed:.0f}ms (>100ms)")

        return embedding.astype(np.float32)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """
        Encode multiple texts into embeddings.

        Args:
            texts: List of texts to encode

        Returns:
            numpy array of shape (n, 384) with float32 values
        """
        if not texts:
            return np.zeros((0, settings.embedding_dim), dtype=np.float32)

        embeddings = self._model.encode(texts, show_progress_bar=False)
        return embeddings.astype(np.float32)

    @property
    def dimension(self) -> int:
        """Return embedding dimension (384 for all-MiniLM-L6-v2)."""
        return settings.embedding_dim


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Get singleton instance of EmbeddingService."""
    return EmbeddingService()
