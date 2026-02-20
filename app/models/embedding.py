from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    film_id = Column(Integer, ForeignKey("films.id"), unique=True, nullable=False)
    vector = Column(LargeBinary, nullable=False)  # 384-dim float32 = 1536 bytes
    model_version = Column(String(50), nullable=False, default="all-MiniLM-L6-v2")

    # Relationship
    film = relationship("Film", back_populates="embedding")

    def __repr__(self):
        return f"<Embedding(film_id={self.film_id}, model='{self.model_version}')>"
