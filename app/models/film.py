from sqlalchemy import Column, Integer, String, Float, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Film(Base):
    __tablename__ = "films"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    overview = Column(Text, nullable=True)
    runtime = Column(Integer, nullable=True)  # minutes
    genres = Column(JSON, nullable=True)  # ["Action", "Comedy"]
    watch_providers = Column(JSON, nullable=True)  # ["Netflix", "Prime"]
    poster_path = Column(String(255), nullable=True)
    vote_average = Column(Float, nullable=True)
    release_date = Column(String(10), nullable=True)  # YYYY-MM-DD

    # Relationship
    embedding = relationship("Embedding", back_populates="film", uselist=False)

    def __repr__(self):
        return f"<Film(id={self.id}, title='{self.title}')>"
