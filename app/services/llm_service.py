"""Gemini LLM Integration Service - Story 3.4"""
import asyncio
import json
import random
import time
from dataclasses import dataclass

import google.generativeai as genai

from app.config import settings


# Mock responses templates for personalized recommendations
MOCK_REASONING_TEMPLATES = {
    "joyeux": [
        "Tu rayonnes de bonne humeur ! Ce film va amplifier cette énergie positive avec son {genre} captivant. Parfait pour prolonger ce moment de bonheur.",
        "Avec ton état d'esprit radieux, ce {genre} lumineux va te faire passer un excellent moment. L'alchimie entre les personnages reflète ta joie actuelle.",
    ],
    "triste": [
        "Parfois, un bon film aide à traverser les moments difficiles. Ce {genre} touchant t'accompagnera avec douceur et te rappellera que les émotions font partie de la vie.",
        "Ce film a cette capacité rare de nous comprendre quand on ne va pas bien. Son {genre} sensible résonnera avec ce que tu ressens.",
    ],
    "stressé": [
        "Tu as besoin de décompresser ! Ce {genre} va te permettre de t'évader complètement et d'oublier tes soucis pendant quelques heures.",
        "Rien de tel qu'un bon {genre} pour relâcher la pression. Ce film te transportera loin de ton stress quotidien.",
    ],
    "curieux": [
        "Ton esprit curieux va adorer ce {genre} qui pose des questions fascinantes. Prépare-toi à être surpris et à réfléchir !",
        "Ce {genre} intelligent va nourrir ta curiosité. Chaque scène apporte son lot de découvertes et de rebondissements.",
    ],
    "romantique": [
        "L'amour est dans l'air ! Ce {genre} va faire battre ton cœur avec son histoire touchante et ses moments magiques.",
        "Parfait pour ton humeur romantique, ce film capture magnifiquement la beauté des sentiments avec son {genre} émouvant.",
    ],
    "aventurier": [
        "Tu veux de l'action ? Ce {genre} palpitant va te tenir en haleine du début à la fin. Accroche-toi !",
        "Ton esprit aventurier va être comblé par ce {genre} épique. Des paysages grandioses et des héros courageux t'attendent.",
    ],
    "nostalgique": [
        "Ce {genre} a cette magie des films qui nous marquent pour toujours. Il va résonner avec tes souvenirs les plus précieux.",
        "Parfait pour ton humeur nostalgique, ce classique du {genre} te ramènera à une époque où tout semblait plus simple.",
    ],
    "default": [
        "Ce {genre} correspond parfaitement à ce que tu recherches ce soir. Son ambiance unique va te captiver dès les premières minutes.",
        "Un excellent choix pour ton humeur actuelle ! Ce {genre} a tout ce qu'il faut pour te faire passer un moment mémorable.",
    ],
}

MOCK_TAGLINES = [
    "Une pépite qui va te surprendre",
    "Un classique incontournable",
    "Pour les amateurs de sensations fortes",
    "Un voyage émotionnel garanti",
    "Du pur divertissement",
    "Une histoire qui reste en tête",
    "À voir absolument ce soir",
    "Le choix parfait pour ton mood",
]


@dataclass
class FilmRecommendation:
    """A film recommendation from the LLM."""
    film_id: int
    title: str
    reasoning: str | None = None
    tagline: str | None = None


@dataclass
class LLMResponse:
    """Response from the LLM service."""
    primary: FilmRecommendation
    secondary: list[FilmRecommendation]
    raw_response: str


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: list[float] = []

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        # Remove old requests
        self.requests = [t for t in self.requests if now - t < self.window]

        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            self.requests = []

        self.requests.append(time.time())


class LLMService:
    """Service for generating recommendations using Gemini."""

    def __init__(self):
        self.model = None
        self.rate_limiter = RateLimiter(
            max_requests=settings.gemini_requests_per_minute,
            window_seconds=60,
        )
        self._initialized = False

    def _initialize(self):
        """Initialize the Gemini model."""
        if self._initialized:
            return

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=settings.gemini_api_key)
        # Use gemini-2.0-flash which is the current available model
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self._initialized = True
        print("Gemini LLM initialized with gemini-2.0-flash")

    def _build_prompt(
        self,
        mood: str,
        duration: str,
        platforms: list[str],
        genres: list[str],
        deep_question: str,
        deep_answer: str,
        candidate_films: list[dict],
    ) -> str:
        """Build the prompt for the LLM."""
        films_context = "\n".join([
            f"- ID:{f['id']} | {f['title']} ({f.get('year', 'N/A')}) | "
            f"Genres: {', '.join(f.get('genres', []))} | "
            f"Note: {f.get('vote_average', 'N/A')}/10 | "
            f"Synopsis: {f.get('overview', 'N/A')[:200]}..."
            for f in candidate_films[:20]
        ])

        return f"""Tu es un expert en recommandation de films. Ton role est de recommander LE film parfait pour l'utilisateur en fonction de son humeur et de ses preferences.

## PROFIL UTILISATEUR

**Humeur actuelle:**
{mood}

**Temps disponible:** {duration}
**Plateformes:** {', '.join(platforms)}
**Genres souhaites:** {', '.join(genres) if genres else 'Surprise (tu choisis)'}

**Question profonde:** {deep_question}
**Reponse:** {deep_answer}

## FILMS CANDIDATS (par pertinence semantique)

{films_context}

## INSTRUCTIONS

Analyse le profil emotionnel de l'utilisateur et selectionne:
1. UN film principal avec une argumentation personnalisee (2-3 phrases expliquant POURQUOI ce film correspond a son etat)
2. 4 films secondaires avec une courte accroche (1 phrase)

Reponds UNIQUEMENT avec ce JSON (pas de texte avant ou apres):
{{
  "primary": {{
    "film_id": <id du film>,
    "title": "<titre>",
    "reasoning": "<argumentation personnalisee 2-3 phrases>"
  }},
  "secondary": [
    {{"film_id": <id>, "title": "<titre>", "tagline": "<accroche 1 phrase>"}},
    {{"film_id": <id>, "title": "<titre>", "tagline": "<accroche 1 phrase>"}},
    {{"film_id": <id>, "title": "<titre>", "tagline": "<accroche 1 phrase>"}},
    {{"film_id": <id>, "title": "<titre>", "tagline": "<accroche 1 phrase>"}}
  ]
}}"""

    async def generate(
        self,
        mood: str,
        duration: str,
        platforms: list[str],
        genres: list[str],
        deep_question: str,
        deep_answer: str,
        candidate_films: list[dict],
    ) -> LLMResponse:
        """
        Generate film recommendations using Gemini.

        Returns:
            LLMResponse with primary and secondary recommendations
        """
        # Use mock mode if enabled or if no API key
        if settings.llm_mock_mode or not settings.gemini_api_key:
            print("[LLM] Using MOCK mode for personalized recommendations")
            return self._mock_response(mood, candidate_films)

        self._initialize()

        # Rate limiting
        await self.rate_limiter.acquire()

        prompt = self._build_prompt(
            mood, duration, platforms, genres,
            deep_question, deep_answer, candidate_films,
        )

        try:
            print(f"[LLM] Calling Gemini with {len(candidate_films)} candidates...")
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            raw_text = response.text.strip()
            print(f"[LLM] Raw response (first 500 chars): {raw_text[:500]}")

            # Parse JSON response
            # Handle potential markdown code blocks
            if raw_text.startswith("```"):
                parts = raw_text.split("```")
                if len(parts) >= 2:
                    raw_text = parts[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                    raw_text = raw_text.strip()

            print(f"[LLM] Cleaned JSON: {raw_text[:300]}")
            data = json.loads(raw_text)

            primary = FilmRecommendation(
                film_id=data["primary"]["film_id"],
                title=data["primary"]["title"],
                reasoning=data["primary"].get("reasoning"),
            )

            secondary = [
                FilmRecommendation(
                    film_id=s["film_id"],
                    title=s["title"],
                    tagline=s.get("tagline"),
                )
                for s in data.get("secondary", [])[:4]
            ]

            print(f"[LLM] Success! Primary: {primary.title}, Reasoning: {primary.reasoning[:50] if primary.reasoning else 'None'}...")
            return LLMResponse(
                primary=primary,
                secondary=secondary,
                raw_response=response.text,
            )

        except json.JSONDecodeError as e:
            print(f"[LLM] JSON parse error: {e}")
            print(f"[LLM] Failed text: {raw_text[:500] if 'raw_text' in dir() else 'N/A'}")
            return self._fallback_response(candidate_films)
        except Exception as e:
            print(f"[LLM] Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_response(candidate_films)

    def _mock_response(self, mood: str, candidate_films: list[dict]) -> LLMResponse:
        """Generate mock personalized response based on mood."""
        if not candidate_films:
            raise ValueError("No candidate films for mock response")

        # Find mood key
        mood_lower = mood.lower()
        mood_key = "default"
        for key in MOCK_REASONING_TEMPLATES.keys():
            if key in mood_lower:
                mood_key = key
                break

        primary = candidate_films[0]
        secondary = candidate_films[1:5]

        # Get genre for template
        primary_genre = primary.get("genres", ["film"])[0] if primary.get("genres") else "film"

        # Generate personalized reasoning
        reasoning_template = random.choice(MOCK_REASONING_TEMPLATES[mood_key])
        reasoning = reasoning_template.format(genre=primary_genre.lower())

        # Generate taglines for secondary films
        used_taglines = set()
        secondary_recs = []
        for s in secondary:
            available_taglines = [t for t in MOCK_TAGLINES if t not in used_taglines]
            if not available_taglines:
                available_taglines = MOCK_TAGLINES
            tagline = random.choice(available_taglines)
            used_taglines.add(tagline)
            secondary_recs.append(
                FilmRecommendation(
                    film_id=s["id"],
                    title=s["title"],
                    tagline=tagline,
                )
            )

        print(f"[LLM] Mock response generated for mood '{mood}': {primary['title']}")
        return LLMResponse(
            primary=FilmRecommendation(
                film_id=primary["id"],
                title=primary["title"],
                reasoning=reasoning,
            ),
            secondary=secondary_recs,
            raw_response="mock_mode",
        )

    def _fallback_response(self, candidate_films: list[dict]) -> LLMResponse:
        """Generate fallback response when LLM fails."""
        if not candidate_films:
            raise ValueError("No candidate films for fallback")

        primary = candidate_films[0]
        secondary = candidate_films[1:5]

        return LLMResponse(
            primary=FilmRecommendation(
                film_id=primary["id"],
                title=primary["title"],
                reasoning="Ce film correspond a ton humeur actuelle et tes preferences.",
            ),
            secondary=[
                FilmRecommendation(
                    film_id=s["id"],
                    title=s["title"],
                    tagline="Une alternative qui pourrait te plaire.",
                )
                for s in secondary
            ],
            raw_response="fallback",
        )


# Singleton
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get singleton instance of LLMService."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
