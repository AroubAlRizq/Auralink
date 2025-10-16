# app/data/models/asr_job.py
"""
ASR Job model - tracks automatic speech recognition job status.
"""

from sqlalchemy import Column, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class AsrJob(Base):
    __tablename__ = "asr_jobs"

    id = Column(Text, primary_key=True)  # Provider job ID
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Text, nullable=False)  # assemblyai, deepgram, whisper, etc.
    callback_url = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="queued")  # queued, processing, completed, error
    error = Column(Text, nullable=True)
    raw = Column(JSONB, nullable=True)  # Optional provider payload
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationship
    meeting = relationship("Meeting", back_populates="asr_jobs")

    # Index
    __table_args__ = (
        Index("ix_asr_jobs_meeting_id", "meeting_id"),
    )

    def __repr__(self):
        return f"<AsrJob(id='{self.id}', provider='{self.provider}', status='{self.status}')>"

