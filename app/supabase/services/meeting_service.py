# app/supabase/services/meeting_service.py
"""
Service class for Meeting model operations with Supabase.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase import Client
from .base_service import BaseService


class MeetingService(BaseService):
    """
    Service for managing meetings in Supabase.
    Handles CRUD operations for the meetings table.
    """
    
    def __init__(self, client: Client):
        """Initialize MeetingService with Supabase client."""
        super().__init__(client, "meetings")
    
    def create_meeting(
        self,
        title: str,
        video_url: Optional[str] = None,
        consent: bool = False,
        status: str = "uploaded"
    ) -> Dict[str, Any]:
        """
        Create a new meeting record.
        
        Args:
            title: Meeting title
            video_url: URL to video file
            consent: User consent flag
            status: Meeting status (default: "uploaded")
            
        Returns:
            Created meeting record
        """
        data = {
            "title": title,
            "video_url": video_url,
            "consent": consent,
            "status": status
        }
        return self.create(data)
    
    def get_meeting(self, meeting_id: str | UUID) -> Optional[Dict[str, Any]]:
        """
        Get a meeting by ID.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            Meeting record or None
        """
        return self.get_by_id(str(meeting_id))
    
    def update_status(self, meeting_id: str | UUID, status: str) -> Dict[str, Any]:
        """
        Update meeting status.
        
        Args:
            meeting_id: Meeting UUID
            status: New status (e.g., "uploaded", "asr_started", "asr_done", "indexed", "summarized", "error")
            
        Returns:
            Updated meeting record
        """
        return self.update(str(meeting_id), {"status": status})
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get meetings by status.
        
        Args:
            status: Status to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of meeting records
        """
        return self.filter({"status": status}, limit=limit)
    
    def get_recent_meetings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent meetings.
        
        Args:
            limit: Maximum number of meetings to return
            
        Returns:
            List of meeting records ordered by created_at descending
        """
        return self.order_by("created_at", ascending=False, limit=limit)
    
    def delete_meeting(self, meeting_id: str | UUID) -> bool:
        """
        Delete a meeting (cascades to related records).
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            True if successful
        """
        return self.delete(str(meeting_id))
    
    def get_meeting_with_relations(self, meeting_id: str | UUID) -> Optional[Dict[str, Any]]:
        """
        Get a meeting with all related data (files, utterances, summary, chunks).
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            Meeting record with nested relations or None
        """
        response = (
            self.table
            .select(
                "*,"
                "files(*),"
                "utterances(*),"
                "summaries(*),"
                "chunks(*),"
                "asr_jobs(*)"
            )
            .eq("id", str(meeting_id))
            .execute()
        )
        return response.data[0] if response.data else None

