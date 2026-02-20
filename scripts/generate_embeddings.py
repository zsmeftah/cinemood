#!/usr/bin/env python
"""Generate SBERT embeddings for all films in the database."""
import argparse
import asyncio
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, func

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import async_session_maker
from app.models import Film, Embedding

BATCH_SIZE = 100


def create_film_text(film: Film) -> str:
    """Create searchable text from film data for embedding."""
    parts = []

    if film.title:
        parts.append(film.title)

    if film.overview:
        parts.append(film.overview)

    if film.genres:
        parts.append(" ".join(film.genres))

    return " ".join(parts)


async def generate_embeddings(batch_size: int = BATCH_SIZE):
    """Generate embeddings for all films without embeddings."""
    print(f"Loading SBERT model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)

    async with async_session_maker() as session:
        # Count films without embeddings
        total_films = await session.scalar(select(func.count(Film.id)))
        films_with_embeddings = await session.scalar(select(func.count(Embedding.id)))
        films_to_process = total_films - films_with_embeddings

        print(f"Total films: {total_films}")
        print(f"Films with embeddings: {films_with_embeddings}")
        print(f"Films to process: {films_to_process}")

        if films_to_process == 0:
            print("All films already have embeddings!")
            return

        # Process in batches
        processed = 0
        offset = 0

        while processed < films_to_process:
            # Get films without embeddings
            result = await session.execute(
                select(Film)
                .outerjoin(Embedding)
                .where(Embedding.id.is_(None))
                .offset(offset)
                .limit(batch_size)
            )
            films = result.scalars().all()

            if not films:
                break

            # Create text for each film
            texts = [create_film_text(film) for film in films]

            # Generate embeddings in batch
            vectors = model.encode(texts, show_progress_bar=False)

            # Save embeddings
            for film, vector in zip(films, vectors):
                embedding = Embedding(
                    film_id=film.id,
                    vector=vector.astype(np.float32).tobytes(),
                    model_version=settings.embedding_model,
                )
                session.add(embedding)

            await session.commit()
            processed += len(films)

            print(f"Progress: {processed}/{films_to_process} embeddings generated")

    print(f"\nComplete! {processed} embeddings generated.")
    print(f"Embedding dimension: {settings.embedding_dim}")


async def main():
    parser = argparse.ArgumentParser(description="Generate SBERT embeddings for films")
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE, help="Batch size for processing"
    )
    args = parser.parse_args()

    await generate_embeddings(args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())
