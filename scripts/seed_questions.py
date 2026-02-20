#!/usr/bin/env python
"""Seed the database with 20 deep questions from PRD section 3.3."""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_maker, engine, Base
from app.models import Question

# 20 Deep Questions from PRD Section 3.3
DEEP_QUESTIONS = [
    {
        "category": "emotion",
        "question_text": "As-tu besoin d'évasion ou de réconfort ce soir ?",
        "options": ["Évasion totale", "Réconfort doux", "Un peu des deux"],
    },
    {
        "category": "preference",
        "question_text": "Préfères-tu rire ou réfléchir ?",
        "options": ["Rire sans réfléchir", "Réfléchir profondément", "Les deux en même temps"],
    },
    {
        "category": "preference",
        "question_text": "Es-tu d'humeur à être surpris ou à rester en terrain connu ?",
        "options": ["Surprends-moi", "Terrain connu", "Surprise légère"],
    },
    {
        "category": "emotion",
        "question_text": "Comment décrirais-tu ton niveau d'énergie actuel ?",
        "options": ["Épuisé·e", "Calme", "Énergique", "Survolté·e"],
    },
    {
        "category": "emotion",
        "question_text": "As-tu besoin de te vider la tête ou de stimuler ton esprit ?",
        "options": ["Vider la tête", "Stimuler l'esprit", "Juste me divertir"],
    },
    {
        "category": "emotion",
        "question_text": "Ressens-tu une forme de stress que tu aimerais évacuer ?",
        "options": ["Oui, beaucoup", "Un peu", "Non, je suis serein·e"],
    },
    {
        "category": "context",
        "question_text": "Tu regardes seul·e ou accompagné·e ?",
        "options": ["Seul·e", "En couple", "Entre amis", "En famille"],
    },
    {
        "category": "emotion",
        "question_text": "As-tu envie de ressentir des émotions fortes ou de rester léger ?",
        "options": ["Émotions fortes", "Rester léger", "Montagnes russes"],
    },
    {
        "category": "emotion",
        "question_text": "Cherches-tu à te sentir moins seul·e ce soir ?",
        "options": ["Oui", "Non", "Je ne sais pas"],
    },
    {
        "category": "preference",
        "question_text": "As-tu des pensées que tu aimerais explorer à travers un film ?",
        "options": ["L'amour", "Le sens de la vie", "L'aventure", "Non, juste du fun"],
    },
    {
        "category": "preference",
        "question_text": "Préfères-tu un film qui te ressemble ou qui te fait découvrir autre chose ?",
        "options": ["Qui me ressemble", "Qui m'ouvre à autre chose", "Peu importe"],
    },
    {
        "category": "preference",
        "question_text": "As-tu besoin d'un happy ending ce soir ?",
        "options": ["Absolument", "Pas forcément", "J'aime les fins ouvertes"],
    },
    {
        "category": "emotion",
        "question_text": "Es-tu nostalgique ou tourné·e vers l'avenir en ce moment ?",
        "options": ["Nostalgique", "Tourné·e vers l'avenir", "Ancré·e dans le présent"],
    },
    {
        "category": "preference",
        "question_text": "Quelle époque t'attire ce soir ?",
        "options": ["Passé/Historique", "Contemporain", "Futuriste", "Intemporel"],
    },
    {
        "category": "preference",
        "question_text": "Quel niveau d'intensité recherches-tu ?",
        "options": ["Doux et apaisant", "Modéré", "Intense", "Extrême"],
    },
    {
        "category": "emotion",
        "question_text": "Es-tu prêt·e à pleurer devant un film ce soir ?",
        "options": ["Oui, j'en ai besoin", "Pourquoi pas", "Non merci"],
    },
    {
        "category": "preference",
        "question_text": "Préfères-tu un classique reconnu ou une pépite méconnue ?",
        "options": ["Classique sûr", "Pépite cachée", "Peu importe"],
    },
    {
        "category": "context",
        "question_text": "Es-tu ouvert·e à un film en VO sous-titrée ?",
        "options": ["Oui", "Seulement si c'est excellent", "Non, VF uniquement"],
    },
    {
        "category": "emotion",
        "question_text": "Qu'est-ce qui te ferait du bien là, maintenant ?",
        "options": ["Rire", "Pleurer", "Frissonner", "Rêver", "Réfléchir"],
    },
    {
        "category": "preference",
        "question_text": "Si ce film pouvait t'apporter une chose, ce serait... ?",
        "options": ["De l'espoir", "De l'adrénaline", "De la paix", "De l'inspiration"],
    },
]


async def seed_questions():
    """Seed the database with deep questions."""
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Check if questions already exist
        result = await session.execute(select(Question))
        existing = result.scalars().all()

        if existing:
            print(f"Database already has {len(existing)} questions.")
            print("Clearing existing questions...")
            for q in existing:
                await session.delete(q)
            await session.commit()

        # Insert questions
        for i, q_data in enumerate(DEEP_QUESTIONS, 1):
            question = Question(
                category=q_data["category"],
                question_text=q_data["question_text"],
                options=q_data["options"],
            )
            session.add(question)
            print(f"Added question {i}: {q_data['question_text'][:50]}...")

        await session.commit()
        print(f"\nSeeded {len(DEEP_QUESTIONS)} deep questions successfully!")

        # Print summary by category
        categories = {}
        for q in DEEP_QUESTIONS:
            cat = q["category"]
            categories[cat] = categories.get(cat, 0) + 1

        print("\nQuestions by category:")
        for cat, count in sorted(categories.items()):
            print(f"  - {cat}: {count}")


if __name__ == "__main__":
    asyncio.run(seed_questions())
