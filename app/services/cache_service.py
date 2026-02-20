"""LLM Response Cache Service - Story 3.5"""
import hashlib
import json
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LLMCache


class CacheService:
    """Service for caching LLM responses with SHA256 hash keys."""

    TTL_DAYS = 7

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def compute_hash(data: dict) -> str:
        """
        Compute SHA256 hash of input data.

        Args:
            data: Dictionary to hash (will be sorted and JSON serialized)

        Returns:
            64-character hex string
        """
        # Sort keys for consistent hashing
        sorted_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_json.encode('utf-8')).hexdigest()

    async def get(self, input_hash: str) -> str | None:
        """
        Get cached response by input hash.

        Args:
            input_hash: SHA256 hash of the input

        Returns:
            Cached response string if found and not expired, None otherwise
        """
        result = await self.db.execute(
            select(LLMCache).where(LLMCache.input_hash == input_hash)
        )
        cache_entry = result.scalar_one_or_none()

        if cache_entry is None:
            return None

        # Check expiration
        if cache_entry.is_expired:
            await self.db.delete(cache_entry)
            await self.db.commit()
            return None

        return cache_entry.response

    async def set(self, input_hash: str, response: str) -> None:
        """
        Store response in cache.

        Args:
            input_hash: SHA256 hash of the input
            response: Response string to cache
        """
        # Check if entry exists
        result = await self.db.execute(
            select(LLMCache).where(LLMCache.input_hash == input_hash)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing entry
            existing.response = response
            existing.created_at = datetime.utcnow()
            existing.expires_at = datetime.utcnow()
            # Recalculate expiry
            cache_entry = LLMCache.create_with_ttl(input_hash, response, self.TTL_DAYS)
            existing.expires_at = cache_entry.expires_at
        else:
            # Create new entry
            cache_entry = LLMCache.create_with_ttl(input_hash, response, self.TTL_DAYS)
            self.db.add(cache_entry)

        await self.db.commit()

    async def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        result = await self.db.execute(
            delete(LLMCache).where(LLMCache.expires_at < datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount
