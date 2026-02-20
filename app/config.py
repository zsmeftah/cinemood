from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # App
    app_name: str = "CinéMood API"
    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/cinemood.db"

    # External APIs
    tmdb_api_key: str = ""
    gemini_api_key: str = ""

    # ML Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    top_k_results: int = 5

    # Rate Limiting
    gemini_requests_per_minute: int = 60

    # Mock mode (use when Gemini API quota is exceeded)
    llm_mock_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directory exists
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)
