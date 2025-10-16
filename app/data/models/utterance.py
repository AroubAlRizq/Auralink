# app/data/models/utterance.py
"""
Utterance model - stores individual speech segments from ASR transcription.
"""

from sqlalchemy import Column, BigInteger, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Utterance(Base):
    __tablename__ = "utterances"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    speaker = Column(Text, nullable=False)  # e.g., SPEAKER_0, SPEAKER_1
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    meeting = relationship("Meeting", back_populates="utterances")

    # Indexes
    __table_args__ = (
        Index("ix_utterances_meeting_id", "meeting_id"),
        Index("ix_utterances_meeting_id_start_seconds", "meeting_id", "start_seconds"),
    )

    def __repr__(self):
        return f"<Utterance(id={self.id}, speaker='{self.speaker}', start={self.start_seconds:.2f}s)>"

