# app/data/models/summary.py
"""
Summary model - stores structured meeting minutes/summary as JSONB.
"""

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Summary(Base):
    __tablename__ = "summaries"

    meeting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
    payload = Column(JSONB, nullable=False)  # Structured minutes/summary
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationship
    meeting = relationship("Meeting", back_populates="summary")

    def __repr__(self):
        return f"<Summary(meeting_id={self.meeting_id})>"

