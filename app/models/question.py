from sqlalchemy import Column, Integer, String, Text, JSON

from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # emotion, context, preference
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # ["Option A", "Option B", ...]

    def __repr__(self):
        return f"<Question(id={self.id}, category='{self.category}')>"
