"""RAG Pipeline Orchestration - Story 3.6"""
import json
import time
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import get_embedding_service
from app.services.film_service import FilmService
from app.services.similarity_service import get_similarity_service
from app.services.llm_service import get_llm_service, LLMResponse
from app.services.cache_service import CacheService
from app.models import Film


@dataclass
class QuizAnswers:
    """Input from quiz."""
    mood: str
    duration: str
    platforms: list[str]
    genres: list[str]
    deep_question_id: int
    deep_question_text: str
    deep_answer: str


@dataclass
class FilmData:
    """Film data for response."""
    id: int
    tmdb_id: int
    title: str
    overview: str | None
    runtime: int | None
    genres: list[str]
    platforms: list[str]
    poster_path: str | None
    vote_average: float | None
    release_date: str | None
    reasoning: str | None = None
    tagline: str | None = None
    similarity_score: float | None = None


@dataclass
class RecommendationResponse:
    """Final recommendation response."""
    primary: FilmData
    secondary: list[FilmData]
    processing_time_ms: int
    from_cache: bool


class RecommendationService:
    """Orchestrates the full RAG pipeline for recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.film_service = FilmService(db)
        self.cache_service = CacheService(db)
        self.embedding_service = get_embedding_service()
        self.similarity_service = get_similarity_service()
        self.llm_service = get_llm_service()

    async def get_recommendations(self, answers: QuizAnswers) -> RecommendationResponse:
        """
        Execute the full RAG pipeline.

        Pipeline: encode → filter → similarity → RAG context → Gemini → response

        Args:
            answers: Quiz answers from the user

        Returns:
            RecommendationResponse with primary and secondary films
        """
        start_time = time.time()

        # 1. Check cache first
        cache_key = CacheService.compute_hash({
            "mood": answers.mood,
            "duration": answers.duration,
            "platforms": sorted(answers.platforms),
            "genres": sorted(answers.genres),
            "deep_question_id": answers.deep_question_id,
            "deep_answer": answers.deep_answer,
        })

        cached_response = await self.cache_service.get(cache_key)
        if cached_response:
            data = json.loads(cached_response)
            elapsed = int((time.time() - start_time) * 1000)
            return RecommendationResponse(
                primary=FilmData(**data["primary"]),
                secondary=[FilmData(**s) for s in data["secondary"]],
                processing_time_ms=elapsed,
                from_cache=True,
            )

        # 2. Encode user mood text
        user_embedding = self.embedding_service.encode(answers.mood)

        # 3. Get filtered films with embeddings
        films_with_embeddings = await self.film_service.get_films_with_embeddings(
            duration=answers.duration,
            platforms=answers.platforms,
            genres=answers.genres,
        )

        if not films_with_embeddings:
            # Fallback: get all films if filters too restrictive
            films_with_embeddings = await self.film_service.get_films_with_embeddings()

        # 4. Load embeddings for similarity search
        film_embeddings = [(film.id, emb) for film, emb in films_with_embeddings]
        filtered_films = [film for film, _ in films_with_embeddings]

        self.similarity_service.load_embeddings(film_embeddings)

        # 5. Find top 20 similar films
        similar_results = self.similarity_service.find_similar(
            user_embedding,
            top_k=20,
            film_id_filter=[f.id for f in filtered_films],
        )

        # 6. Get full film data for candidates
        candidate_ids = [r.film_id for r in similar_results]
        candidate_films = await self.film_service.get_films_by_ids(candidate_ids)

        # Build similarity score map
        score_map = {r.film_id: r.score for r in similar_results}

        # Prepare candidate data for LLM
        candidates_for_llm = [
            {
                "id": f.id,
                "title": f.title,
                "year": f.release_date[:4] if f.release_date else None,
                "genres": f.genres or [],
                "vote_average": f.vote_average,
                "overview": f.overview,
            }
            for f in candidate_films
        ]

        # 7. Call LLM for recommendations
        llm_response = await self.llm_service.generate(
            mood=answers.mood,
            duration=answers.duration,
            platforms=answers.platforms,
            genres=answers.genres,
            deep_question=answers.deep_question_text,
            deep_answer=answers.deep_answer,
            candidate_films=candidates_for_llm,
        )

        # 8. Build response
        film_map = {f.id: f for f in candidate_films}

        primary_film = film_map.get(llm_response.primary.film_id)
        if not primary_film and candidate_films:
            primary_film = candidate_films[0]

        primary_data = self._build_film_data(
            primary_film,
            reasoning=llm_response.primary.reasoning,
            similarity_score=score_map.get(primary_film.id) if primary_film else None,
        )

        secondary_data = []
        for rec in llm_response.secondary:
            film = film_map.get(rec.film_id)
            if film:
                secondary_data.append(self._build_film_data(
                    film,
                    tagline=rec.tagline,
                    similarity_score=score_map.get(film.id),
                ))

        # Fill secondary if needed
        if len(secondary_data) < 4:
            used_ids = {primary_data.id} | {s.id for s in secondary_data}
            for film in candidate_films:
                if film.id not in used_ids:
                    secondary_data.append(self._build_film_data(
                        film,
                        tagline="Une alternative qui pourrait te plaire.",
                        similarity_score=score_map.get(film.id),
                    ))
                    if len(secondary_data) >= 4:
                        break

        elapsed = int((time.time() - start_time) * 1000)

        response = RecommendationResponse(
            primary=primary_data,
            secondary=secondary_data[:4],
            processing_time_ms=elapsed,
            from_cache=False,
        )

        # 9. Cache the response
        cache_data = {
            "primary": asdict(response.primary),
            "secondary": [asdict(s) for s in response.secondary],
        }
        await self.cache_service.set(cache_key, json.dumps(cache_data))

        return response

    def _build_film_data(
        self,
        film: Film,
        reasoning: str | None = None,
        tagline: str | None = None,
        similarity_score: float | None = None,
    ) -> FilmData:
        """Build FilmData from Film model."""
        return FilmData(
            id=film.id,
            tmdb_id=film.tmdb_id,
            title=film.title,
            overview=film.overview,
            runtime=film.runtime,
            genres=film.genres or [],
            platforms=film.watch_providers or [],
            poster_path=film.poster_path,
            vote_average=film.vote_average,
            release_date=film.release_date,
            reasoning=reasoning,
            tagline=tagline,
            similarity_score=similarity_score,
        )
