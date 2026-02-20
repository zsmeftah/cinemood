"""Quiz API Endpoints - Story 3.7"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.recommendation_service import (
    RecommendationService,
    QuizAnswers,
    RecommendationResponse,
    FilmData,
)

router = APIRouter(prefix="/api", tags=["recommendations"])


class DeepQuestionInput(BaseModel):
    """Deep question input from quiz."""
    question_id: int
    question_text: str = ""
    answer: str


class QuizInput(BaseModel):
    """Quiz submission input."""
    mood: str = Field(..., min_length=1, max_length=500)
    duration: str = Field(..., pattern=r"^(<90|90-120|>120|any)$")
    platforms: list[str] = Field(..., min_length=1)
    genres: list[str] = Field(..., min_length=1)
    deep_question: DeepQuestionInput


class FilmResponse(BaseModel):
    """Film data in response."""
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

    class Config:
        from_attributes = True


class RecommendResponse(BaseModel):
    """Full recommendation response."""
    primary: FilmResponse
    secondary: list[FilmResponse]
    processing_time_ms: int
    from_cache: bool


@router.post("/recommend", response_model=RecommendResponse)
async def get_recommendations(
    quiz_input: QuizInput,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit quiz answers and get film recommendations.

    The pipeline:
    1. Encode mood text with SBERT
    2. Filter films by duration, platforms, genres
    3. Compute cosine similarity
    4. Generate recommendations with Gemini LLM
    5. Return primary + 4 secondary recommendations
    """
    try:
        service = RecommendationService(db)

        answers = QuizAnswers(
            mood=quiz_input.mood,
            duration=quiz_input.duration,
            platforms=quiz_input.platforms,
            genres=quiz_input.genres,
            deep_question_id=quiz_input.deep_question.question_id,
            deep_question_text=quiz_input.deep_question.question_text,
            deep_answer=quiz_input.deep_question.answer,
        )

        response = await service.get_recommendations(answers)

        return RecommendResponse(
            primary=FilmResponse(**response.primary.__dict__),
            secondary=[FilmResponse(**s.__dict__) for s in response.secondary],
            processing_time_ms=response.processing_time_ms,
            from_cache=response.from_cache,
        )

    except Exception as e:
        print(f"Recommendation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}",
        )
