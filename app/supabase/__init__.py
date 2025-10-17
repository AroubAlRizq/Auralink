# app/supabase/__init__.py
"""
Supabase integration module for Auralink.
Provides Supabase client and services for all ORM models.
"""

from .client import get_supabase_client, get_admin_client
from .services.meeting_service import MeetingService
from .services.file_service import FileService
from .services.chunk_service import ChunkService
from .services.summary_service import SummaryService
from .services.utterance_service import UtteranceService
from .services.asr_job_service import AsrJobService

__all__ = [
    "get_supabase_client",
    "get_admin_client",
    "MeetingService",
    "FileService",
    "ChunkService",
    "SummaryService",
    "UtteranceService",
    "AsrJobService",
]

