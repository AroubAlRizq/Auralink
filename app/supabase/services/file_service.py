# app/supabase/services/file_service.py
"""
Service class for File model operations with Supabase.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase import Client
from .base_service import BaseService


class FileService(BaseService):
    """
    Service for managing files in Supabase.
    Handles CRUD operations for the files table.
    """
    
    def __init__(self, client: Client):
        """Initialize FileService with Supabase client."""
        super().__init__(client, "files")
    
    def create_file(
        self,
        meeting_id: str | UUID,
        path: str,
        kind: str,
        public_url: Optional[str] = None,
        size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new file record.
        
        Args:
            meeting_id: Associated meeting UUID
            path: File path (bucket/key)
            kind: File type (upload, narration, summary, other)
            public_url: Public URL to access file
            size_bytes: File size in bytes
            mime_type: MIME type of file
            
        Returns:
            Created file record
        """
        data = {
            "meeting_id": str(meeting_id),
            "path": path,
            "kind": kind,
            "public_url": public_url,
            "size_bytes": size_bytes,
            "mime_type": mime_type
        }
        return self.create(data)
    
    def get_files_by_meeting(self, meeting_id: str | UUID) -> List[Dict[str, Any]]:
        """
        Get all files for a specific meeting.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            List of file records
        """
        return self.filter({"meeting_id": str(meeting_id)})
    
    def get_files_by_kind(
        self,
        meeting_id: str | UUID,
        kind: str
    ) -> List[Dict[str, Any]]:
        """
        Get files by meeting and kind.
        
        Args:
            meeting_id: Meeting UUID
            kind: File type (upload, narration, summary, other)
            
        Returns:
            List of file records
        """
        response = (
            self.table
            .select("*")
            .eq("meeting_id", str(meeting_id))
            .eq("kind", kind)
            .execute()
        )
        return response.data if response.data else []
    
    def update_public_url(self, file_id: int, public_url: str) -> Dict[str, Any]:
        """
        Update the public URL of a file.
        
        Args:
            file_id: File ID
            public_url: New public URL
            
        Returns:
            Updated file record
        """
        return self.update(file_id, {"public_url": public_url})
    
    def delete_file(self, file_id: int) -> bool:
        """
        Delete a file record.
        
        Args:
            file_id: File ID
            
        Returns:
            True if successful
        """
        return self.delete(file_id)

