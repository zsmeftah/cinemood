from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Question

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("/random")
async def get_random_question(db: AsyncSession = Depends(get_db)):
    """Get a random deep question from the database."""
    # Get a random question using SQL
    result = await db.execute(
        select(Question).order_by(func.random()).limit(1)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="No questions found")

    return {
        "id": question.id,
        "category": question.category,
        "question_text": question.question_text,
        "options": question.options,
    }


@router.get("/")
async def get_all_questions(db: AsyncSession = Depends(get_db)):
    """Get all deep questions."""
    result = await db.execute(select(Question))
    questions = result.scalars().all()

    return [
        {
            "id": q.id,
            "category": q.category,
            "question_text": q.question_text,
            "options": q.options,
        }
        for q in questions
    ]
