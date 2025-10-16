# app/data/models/__init__.py
"""
SQLAlchemy ORM models for Supabase database.

All models are exported from this module for easy importing.
Usage:
    from app.data.models import Meeting, Utterance, Summary, Chunk, AsrJob, File
    from app.data.models import Base, engine, SessionLocal, get_db
"""

from .base import Base, engine, SessionLocal, get_db
from .meeting import Meeting
from .utterance import Utterance
from .summary import Summary
from .chunk import Chunk
from .asr_job import AsrJob
from .file import File

__all__ = [
    # Base components
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    # Models
    "Meeting",
    "Utterance",
    "Summary",
    "Chunk",
    "AsrJob",
    "File",
]


def create_all_tables():
    """
    Create all tables in the database.
    Note: This won't create the IVFFLAT index on chunks.embedding
    You need to run that SQL manually after calling this function.
    """
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully!")
    print("\n⚠️  Don't forget to create the vector index manually:")
    print("   CREATE INDEX chunks_embedding_ivfflat_idx ON chunks")
    print("   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")


def drop_all_tables():
    """
    Drop all tables from the database.
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped!")

