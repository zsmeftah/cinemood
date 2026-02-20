#!/usr/bin/env python
"""Sync popular films from TMDB API to database."""
import argparse
import asyncio
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import select

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import async_session_maker, engine, Base
from app.models import Film

# TMDB API Configuration
TMDB_BASE_URL = "https://api.themoviedb.org/3"
RATE_LIMIT_REQUESTS = 40
RATE_LIMIT_WINDOW = 10  # seconds


class TMDBSyncer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.request_times: list[float] = []
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _rate_limit(self):
        """Enforce rate limiting: 40 requests per 10 seconds."""
        now = time.time()
        # Remove requests older than window
        self.request_times = [t for t in self.request_times if now - t < RATE_LIMIT_WINDOW]

        if len(self.request_times) >= RATE_LIMIT_REQUESTS:
            sleep_time = RATE_LIMIT_WINDOW - (now - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                self.request_times = []

        self.request_times.append(time.time())

    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make a rate-limited GET request to TMDB API."""
        await self._rate_limit()

        params = params or {}
        params["api_key"] = self.api_key

        url = f"{TMDB_BASE_URL}{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_popular_movies(self, page: int = 1) -> dict:
        """Get a page of popular movies."""
        return await self._get(
            "/movie/popular",
            {"language": "fr-FR", "page": page, "region": "FR"},
        )

    async def get_movie_details(self, movie_id: int) -> dict:
        """Get detailed movie information."""
        return await self._get(f"/movie/{movie_id}", {"language": "fr-FR"})

    async def get_watch_providers(self, movie_id: int) -> list[str]:
        """Get streaming providers for France."""
        try:
            data = await self._get(f"/movie/{movie_id}/watch/providers")
            fr_providers = data.get("results", {}).get("FR", {})

            # Get flatrate (subscription) providers
            providers = []
            for provider in fr_providers.get("flatrate", []):
                providers.append(provider["provider_name"])

            return providers
        except Exception:
            return []

    async def sync_movies(self, limit: int = 5000):
        """Sync popular movies to database."""
        # Ensure tables exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        movies_synced = 0
        page = 1
        max_pages = (limit // 20) + 1  # TMDB returns 20 results per page

        print(f"Starting TMDB sync for {limit} films...")

        async with async_session_maker() as session:
            while movies_synced < limit and page <= max_pages:
                try:
                    # Get popular movies page
                    data = await self.get_popular_movies(page)
                    movies = data.get("results", [])

                    if not movies:
                        break

                    for movie in movies:
                        if movies_synced >= limit:
                            break

                        tmdb_id = movie["id"]

                        # Check if already exists
                        result = await session.execute(
                            select(Film).where(Film.tmdb_id == tmdb_id)
                        )
                        if result.scalar_one_or_none():
                            continue

                        # Get full movie details (includes runtime, genres)
                        try:
                            details = await self.get_movie_details(tmdb_id)
                        except Exception:
                            details = movie

                        # Get watch providers
                        watch_providers = await self.get_watch_providers(tmdb_id)

                        # Create film record
                        film = Film(
                            tmdb_id=tmdb_id,
                            title=details.get("title", movie.get("title", "")),
                            overview=details.get("overview", movie.get("overview", "")),
                            runtime=details.get("runtime"),
                            genres=[g["name"] for g in details.get("genres", [])],
                            watch_providers=watch_providers,
                            poster_path=details.get("poster_path", movie.get("poster_path")),
                            vote_average=details.get("vote_average", movie.get("vote_average")),
                            release_date=details.get("release_date", movie.get("release_date")),
                        )

                        session.add(film)
                        movies_synced += 1

                        # Log progress every 100 films
                        if movies_synced % 100 == 0:
                            await session.commit()
                            print(f"Progress: {movies_synced}/{limit} films synced")

                    page += 1

                except httpx.HTTPStatusError as e:
                    print(f"HTTP error: {e}")
                    if e.response.status_code == 429:
                        print("Rate limited, waiting 10 seconds...")
                        await asyncio.sleep(10)
                    continue
                except Exception as e:
                    print(f"Error syncing page {page}: {e}")
                    continue

            # Final commit
            await session.commit()

        print(f"\nSync complete! {movies_synced} films synced to database.")

    async def close(self):
        await self.client.aclose()


async def main():
    parser = argparse.ArgumentParser(description="Sync films from TMDB API")
    parser.add_argument("--limit", type=int, default=5000, help="Number of films to sync")
    args = parser.parse_args()

    if not settings.tmdb_api_key:
        print("Error: TMDB_API_KEY not set in environment or .env file")
        print("Get your API key from: https://www.themoviedb.org/settings/api")
        sys.exit(1)

    syncer = TMDBSyncer(settings.tmdb_api_key)
    try:
        await syncer.sync_movies(args.limit)
    finally:
        await syncer.close()


if __name__ == "__main__":
    asyncio.run(main())
