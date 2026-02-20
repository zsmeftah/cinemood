#!/usr/bin/env python
"""Initialize the database with all tables."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base
from app.models import Film, Embedding, LLMCache, Question  # noqa: F401


async def init_database():
    """Create all tables in the database."""
    print("Initializing CinéMood database...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Get table names
    async with engine.begin() as conn:
        result = await conn.run_sync(
            lambda sync_conn: Base.metadata.tables.keys()
        )
        tables = list(result)

    print(f"Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")

    print("\nDatabase initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
