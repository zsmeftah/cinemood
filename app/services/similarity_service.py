"""Cosine Similarity Search Service - Story 3.3"""
import time
from dataclasses import dataclass

import numpy as np

from app.config import settings


@dataclass
class SimilarityResult:
    """Result of similarity search."""
    film_id: int
    score: float


class SimilarityService:
    """Service for computing cosine similarity between embeddings."""

    def __init__(self):
        self.film_embeddings: np.ndarray | None = None
        self.film_ids: list[int] = []

    def load_embeddings(self, films_with_embeddings: list[tuple[int, bytes]]):
        """
        Load film embeddings into memory for fast similarity search.

        Args:
            films_with_embeddings: List of (film_id, embedding_bytes) tuples
        """
        if not films_with_embeddings:
            self.film_embeddings = np.zeros((0, settings.embedding_dim), dtype=np.float32)
            self.film_ids = []
            return

        self.film_ids = [fid for fid, _ in films_with_embeddings]
        embeddings = []

        for _, emb_bytes in films_with_embeddings:
            vector = np.frombuffer(emb_bytes, dtype=np.float32)
            embeddings.append(vector)

        self.film_embeddings = np.vstack(embeddings)
        # Normalize for faster cosine computation
        norms = np.linalg.norm(self.film_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        self.film_embeddings = self.film_embeddings / norms

        print(f"Loaded {len(self.film_ids)} film embeddings into memory")

    def find_similar(
        self,
        user_embedding: np.ndarray,
        top_k: int = 20,
        film_id_filter: list[int] | None = None,
    ) -> list[SimilarityResult]:
        """
        Find top-k most similar films to user embedding.

        Args:
            user_embedding: User's mood embedding (384 dims)
            top_k: Number of top results to return
            film_id_filter: Optional list of film IDs to restrict search to

        Returns:
            List of SimilarityResult sorted by descending similarity score
        """
        if self.film_embeddings is None or len(self.film_ids) == 0:
            return []

        start = time.time()

        # Normalize user embedding
        user_norm = np.linalg.norm(user_embedding)
        if user_norm == 0:
            return []
        user_normalized = user_embedding / user_norm

        # Filter embeddings if needed
        if film_id_filter:
            filter_set = set(film_id_filter)
            mask = np.array([fid in filter_set for fid in self.film_ids])
            filtered_embeddings = self.film_embeddings[mask]
            filtered_ids = [fid for fid, m in zip(self.film_ids, mask) if m]
        else:
            filtered_embeddings = self.film_embeddings
            filtered_ids = self.film_ids

        if len(filtered_ids) == 0:
            return []

        # Compute cosine similarity (dot product since vectors are normalized)
        similarities = np.dot(filtered_embeddings, user_normalized)

        # Get top-k indices
        if len(similarities) <= top_k:
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        elapsed = (time.time() - start) * 1000  # ms
        if elapsed > 100:
            print(f"Warning: Similarity search took {elapsed:.0f}ms (>100ms)")

        # Build results
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            # Clamp to [0, 1] range
            score = max(0.0, min(1.0, score))
            results.append(SimilarityResult(
                film_id=filtered_ids[idx],
                score=score,
            ))

        return results


# Singleton instance
_similarity_service: SimilarityService | None = None


def get_similarity_service() -> SimilarityService:
    """Get singleton instance of SimilarityService."""
    global _similarity_service
    if _similarity_service is None:
        _similarity_service = SimilarityService()
    return _similarity_service
