from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.questions import router as questions_router
from app.api.recommend import router as recommend_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()

    # Preload SBERT model
    print("Preloading SBERT model...")
    from app.services.embedding_service import get_embedding_service
    get_embedding_service()

    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(questions_router)
app.include_router(recommend_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
