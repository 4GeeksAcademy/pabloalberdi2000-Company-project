from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Note(Base):
    """
    Note model for storing comments and observations about candidates.
    Used by HR team (Ashley Turner) to track interview feedback, impressions, etc.
    """
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to candidate
    candidate = relationship("Candidate", back_populates="notes")

    def __repr__(self):
        return f"<Note(id={self.id}, candidate_id={self.candidate_id}, author='{self.author}')>"
