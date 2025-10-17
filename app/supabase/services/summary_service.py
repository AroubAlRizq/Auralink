# app/supabase/services/summary_service.py
"""
Service class for Summary model operations with Supabase.
"""

from typing import Dict, Any, Optional
from uuid import UUID
from supabase import Client
from .base_service import BaseService


class SummaryService(BaseService):
    """
    Service for managing meeting summaries in Supabase.
    Handles CRUD operations for the summaries table.
    """
    
    def __init__(self, client: Client):
        """Initialize SummaryService with Supabase client."""
        super().__init__(client, "summaries")
    
    def create_summary(
        self,
        meeting_id: str | UUID,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new summary record.
        
        Args:
            meeting_id: Associated meeting UUID (primary key)
            payload: Structured summary data (stored as JSONB)
            
        Returns:
            Created summary record
        """
        data = {
            "meeting_id": str(meeting_id),
            "payload": payload
        }
        return self.create(data)
    
    def get_summary(self, meeting_id: str | UUID) -> Optional[Dict[str, Any]]:
        """
        Get summary for a specific meeting.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            Summary record or None
        """
        return self.get_by_id(str(meeting_id), id_column="meeting_id")
    
    def update_summary(
        self,
        meeting_id: str | UUID,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing summary.
        
        Args:
            meeting_id: Meeting UUID
            payload: Updated summary data
            
        Returns:
            Updated summary record
        """
        return self.update(str(meeting_id), {"payload": payload}, id_column="meeting_id")
    
    def upsert_summary(
        self,
        meeting_id: str | UUID,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create or update a summary (upsert operation).
        
        Args:
            meeting_id: Meeting UUID
            payload: Summary data
            
        Returns:
            Summary record
        """
        data = {
            "meeting_id": str(meeting_id),
            "payload": payload
        }
        response = (
            self.table
            .upsert(data, on_conflict="meeting_id")
            .execute()
        )
        return response.data[0] if response.data else None
    
    def delete_summary(self, meeting_id: str | UUID) -> bool:
        """
        Delete a summary.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            True if successful
        """
        return self.delete(str(meeting_id), id_column="meeting_id")
    
    def get_summary_field(
        self,
        meeting_id: str | UUID,
        field_path: str
    ) -> Any:
        """
        Get a specific field from the summary payload using JSON path.
        
        Args:
            meeting_id: Meeting UUID
            field_path: JSON path to field (e.g., "title", "action_items")
            
        Returns:
            Field value or None
        """
        summary = self.get_summary(meeting_id)
        if summary and "payload" in summary:
            # Navigate the field path
            value = summary["payload"]
            for key in field_path.split("."):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        return None

