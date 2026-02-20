"""Film Filtering Service - Story 3.2"""
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Film, Embedding


class FilmService:
    """Service for filtering and retrieving films from the database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def filter_films(
        self,
        duration: str | None = None,
        platforms: list[str] | None = None,
        genres: list[str] | None = None,
    ) -> list[Film]:
        """
        Filter films by duration, platforms, and genres.

        Args:
            duration: One of '<90', '90-120', '>120', 'any', or None
            platforms: List of platform names (OR logic - film has at least one)
            genres: List of genre names (OR logic - film matches at least one)
                   'surprise' genre means no genre filter

        Returns:
            List of Film objects matching ALL criteria
        """
        query = select(Film).join(Embedding)  # Only films with embeddings

        conditions = []

        # Duration filter
        if duration and duration != 'any':
            if duration == '<90':
                conditions.append(Film.runtime < 90)
            elif duration == '90-120':
                conditions.append(and_(Film.runtime >= 90, Film.runtime <= 120))
            elif duration == '>120':
                conditions.append(Film.runtime > 120)

        # Platform filter (JSON contains check)
        if platforms:
            # SQLite JSON: check if any platform is in watch_providers
            platform_conditions = []
            for platform in platforms:
                if platform != 'other':
                    # Use JSON contains for each platform
                    platform_conditions.append(
                        Film.watch_providers.contains(platform)
                    )
            if platform_conditions:
                conditions.append(or_(*platform_conditions))

        # Genre filter (JSON contains check)
        if genres and 'surprise' not in genres:
            genre_conditions = []
            for genre in genres:
                genre_conditions.append(Film.genres.contains(genre))
            if genre_conditions:
                conditions.append(or_(*genre_conditions))

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_films_with_embeddings(
        self,
        duration: str | None = None,
        platforms: list[str] | None = None,
        genres: list[str] | None = None,
    ) -> list[tuple[Film, bytes]]:
        """
        Get filtered films with their embedding vectors.

        Returns:
            List of (Film, embedding_bytes) tuples
        """
        query = select(Film, Embedding.vector).join(Embedding)

        conditions = []

        # Duration filter
        if duration and duration != 'any':
            if duration == '<90':
                conditions.append(Film.runtime < 90)
            elif duration == '90-120':
                conditions.append(and_(Film.runtime >= 90, Film.runtime <= 120))
            elif duration == '>120':
                conditions.append(Film.runtime > 120)

        # Platform filter
        if platforms:
            platform_conditions = []
            for platform in platforms:
                if platform != 'other':
                    platform_conditions.append(
                        Film.watch_providers.contains(platform)
                    )
            if platform_conditions:
                conditions.append(or_(*platform_conditions))

        # Genre filter
        if genres and 'surprise' not in genres:
            genre_conditions = []
            for genre in genres:
                genre_conditions.append(Film.genres.contains(genre))
            if genre_conditions:
                conditions.append(or_(*genre_conditions))

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def get_film_by_id(self, film_id: int) -> Film | None:
        """Get a single film by ID."""
        result = await self.db.execute(select(Film).where(Film.id == film_id))
        return result.scalar_one_or_none()

    async def get_films_by_ids(self, film_ids: list[int]) -> list[Film]:
        """Get multiple films by their IDs, preserving order."""
        if not film_ids:
            return []

        result = await self.db.execute(
            select(Film).where(Film.id.in_(film_ids))
        )
        films = {f.id: f for f in result.scalars().all()}
        # Preserve order
        return [films[fid] for fid in film_ids if fid in films]
