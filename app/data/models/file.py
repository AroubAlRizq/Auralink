# app/data/models/file.py
"""
File model - stores metadata about uploaded/generated files.
"""

from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class File(Base):
    __tablename__ = "files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    path = Column(Text, nullable=False)  # bucket/key
    public_url = Column(Text, nullable=True)
    kind = Column(Text, nullable=False)  # upload, narration, summary, other
    size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    meeting = relationship("Meeting", back_populates="files")

    # Index
    __table_args__ = (
        Index("ix_files_meeting_id", "meeting_id"),
    )

    def __repr__(self):
        return f"<File(id={self.id}, kind='{self.kind}', path='{self.path}')>"

