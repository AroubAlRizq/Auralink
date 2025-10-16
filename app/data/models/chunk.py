# app/data/models/chunk.py
"""
Chunk model - stores text chunks with embeddings for RAG/semantic search.
Uses pgvector extension for vector similarity search.
"""

from sqlalchemy import Column, BigInteger, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    speaker = Column(Text, nullable=True)  # ASR speaker or WINDOW_#
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    topic = Column(Text, nullable=True)  # e.g., asr, multimodal_narration
    text = Column(Text, nullable=False)
    embedding = Column(Vector(3072), nullable=True)  # 3072 for text-embedding-3-large
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    meeting = relationship("Meeting", back_populates="chunks")

    # Indexes
    __table_args__ = (
        Index("ix_chunks_meeting_id", "meeting_id"),
        Index("ix_chunks_meeting_id_start_seconds", "meeting_id", "start_seconds"),
        # IVFFLAT index for vector similarity search
        # Note: Create this index manually after table creation:
        # CREATE INDEX chunks_embedding_ivfflat_idx ON chunks 
        # USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    )

    def __repr__(self):
        return f"<Chunk(id={self.id}, topic='{self.topic}', start={self.start_seconds:.2f}s)>"

