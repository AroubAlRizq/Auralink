# app/data/models/meeting.py
"""
Meeting model - stores metadata about uploaded meetings/videos.
"""

from sqlalchemy import Column, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    video_url = Column(Text, nullable=True)
    consent = Column(Boolean, default=False, nullable=False)
    status = Column(
        Text,
        nullable=False,
        default="uploaded"
        # Valid values: uploaded, asr_started, asr_done, indexed, summarized, error
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    utterances = relationship("Utterance", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="meeting", cascade="all, delete-orphan")
    asr_jobs = relationship("AsrJob", back_populates="meeting", cascade="all, delete-orphan")
    files = relationship("File", back_populates="meeting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meeting(id={self.id}, title='{self.title}', status='{self.status}')>"

