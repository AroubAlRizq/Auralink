# app/supabase/services/__init__.py
"""
Service classes for interacting with Supabase tables.
Each service corresponds to an ORM model.
"""

from .base_service import BaseService
from .meeting_service import MeetingService
from .file_service import FileService
from .chunk_service import ChunkService
from .summary_service import SummaryService
from .utterance_service import UtteranceService
from .asr_job_service import AsrJobService

__all__ = [
    "BaseService",
    "MeetingService",
    "FileService",
    "ChunkService",
    "SummaryService",
    "UtteranceService",
    "AsrJobService",
]

