# app/supabase/services/asr_job_service.py
"""
Service class for AsrJob model operations with Supabase.
Tracks automatic speech recognition job status.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase import Client
from .base_service import BaseService


class AsrJobService(BaseService):
    """
    Service for managing ASR jobs in Supabase.
    Handles CRUD operations for the asr_jobs table.
    """
    
    def __init__(self, client: Client):
        """Initialize AsrJobService with Supabase client."""
        super().__init__(client, "asr_jobs")
    
    def create_asr_job(
        self,
        job_id: str,
        meeting_id: str | UUID,
        provider: str,
        callback_url: Optional[str] = None,
        status: str = "queued",
        raw: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new ASR job record.
        
        Args:
            job_id: Provider job ID (primary key)
            meeting_id: Associated meeting UUID
            provider: ASR provider (assemblyai, deepgram, whisper, etc.)
            callback_url: Webhook callback URL
            status: Job status (queued, processing, completed, error)
            raw: Optional provider-specific payload
            
        Returns:
            Created ASR job record
        """
        data = {
            "id": job_id,
            "meeting_id": str(meeting_id),
            "provider": provider,
            "callback_url": callback_url,
            "status": status,
            "raw": raw
        }
        return self.create(data)
    
    def get_asr_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an ASR job by ID.
        
        Args:
            job_id: Provider job ID
            
        Returns:
            ASR job record or None
        """
        return self.get_by_id(job_id)
    
    def get_jobs_by_meeting(
        self,
        meeting_id: str | UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all ASR jobs for a specific meeting.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            List of ASR job records
        """
        return self.filter({"meeting_id": str(meeting_id)})
    
    def get_jobs_by_status(
        self,
        status: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ASR jobs by status.
        
        Args:
            status: Status to filter by (queued, processing, completed, error)
            limit: Maximum number of records to return
            
        Returns:
            List of ASR job records
        """
        return self.filter({"status": status}, limit=limit)
    
    def get_jobs_by_provider(
        self,
        provider: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ASR jobs by provider.
        
        Args:
            provider: Provider name
            limit: Maximum number of records to return
            
        Returns:
            List of ASR job records
        """
        return self.filter({"provider": provider}, limit=limit)
    
    def update_status(
        self,
        job_id: str,
        status: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update job status.
        
        Args:
            job_id: Provider job ID
            status: New status
            error: Error message if status is "error"
            
        Returns:
            Updated ASR job record
        """
        data = {"status": status}
        if error:
            data["error"] = error
        return self.update(job_id, data)
    
    def update_raw_payload(
        self,
        job_id: str,
        raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update the raw provider payload.
        
        Args:
            job_id: Provider job ID
            raw: Provider-specific payload
            
        Returns:
            Updated ASR job record
        """
        return self.update(job_id, {"raw": raw})
    
    def mark_completed(self, job_id: str) -> Dict[str, Any]:
        """
        Mark an ASR job as completed.
        
        Args:
            job_id: Provider job ID
            
        Returns:
            Updated ASR job record
        """
        return self.update_status(job_id, "completed")
    
    def mark_error(self, job_id: str, error_message: str) -> Dict[str, Any]:
        """
        Mark an ASR job as failed with error message.
        
        Args:
            job_id: Provider job ID
            error_message: Error description
            
        Returns:
            Updated ASR job record
        """
        return self.update_status(job_id, "error", error=error_message)
    
    def delete_asr_job(self, job_id: str) -> bool:
        """
        Delete an ASR job record.
        
        Args:
            job_id: Provider job ID
            
        Returns:
            True if successful
        """
        return self.delete(job_id)

