from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base


class LLMCache(Base):
    __tablename__ = "llm_cache"

    id = Column(Integer, primary_key=True, index=True)
    input_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA256
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    @classmethod
    def create_with_ttl(cls, input_hash: str, response: str, ttl_days: int = 7):
        now = datetime.utcnow()
        return cls(
            input_hash=input_hash,
            response=response,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
        )

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def __repr__(self):
        return f"<LLMCache(hash='{self.input_hash[:8]}...', expires={self.expires_at})>"
