# app/supabase/services/utterance_service.py
"""
Service class for Utterance model operations with Supabase.
Handles individual speech segments from ASR transcription.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase import Client
from .base_service import BaseService


class UtteranceService(BaseService):
    """
    Service for managing utterances (ASR speech segments) in Supabase.
    Handles CRUD operations for the utterances table.
    """
    
    def __init__(self, client: Client):
        """Initialize UtteranceService with Supabase client."""
        super().__init__(client, "utterances")
    
    def create_utterance(
        self,
        meeting_id: str | UUID,
        speaker: str,
        text: str,
        start_seconds: float,
        end_seconds: float
    ) -> Dict[str, Any]:
        """
        Create a new utterance record.
        
        Args:
            meeting_id: Associated meeting UUID
            speaker: Speaker identifier (e.g., SPEAKER_0, SPEAKER_1)
            text: Transcribed text
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            
        Returns:
            Created utterance record
        """
        data = {
            "meeting_id": str(meeting_id),
            "speaker": speaker,
            "text": text,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds
        }
        return self.create(data)
    
    def create_utterances_batch(
        self,
        utterances: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create multiple utterances at once.
        
        Args:
            utterances: List of utterance data dictionaries
            
        Returns:
            List of created utterance records
        """
        return self.create_many(utterances)
    
    def get_utterances_by_meeting(
        self,
        meeting_id: str | UUID,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all utterances for a specific meeting.
        
        Args:
            meeting_id: Meeting UUID
            limit: Maximum number of utterances to return
            
        Returns:
            List of utterance records ordered by start_seconds
        """
        query = (
            self.table
            .select("*")
            .eq("meeting_id", str(meeting_id))
            .order("start_seconds", desc=False)
        )
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        return response.data if response.data else []
    
    def get_utterances_by_speaker(
        self,
        meeting_id: str | UUID,
        speaker: str
    ) -> List[Dict[str, Any]]:
        """
        Get utterances by a specific speaker.
        
        Args:
            meeting_id: Meeting UUID
            speaker: Speaker identifier
            
        Returns:
            List of utterance records ordered by time
        """
        response = (
            self.table
            .select("*")
            .eq("meeting_id", str(meeting_id))
            .eq("speaker", speaker)
            .order("start_seconds", desc=False)
            .execute()
        )
        return response.data if response.data else []
    
    def get_utterances_by_time_range(
        self,
        meeting_id: str | UUID,
        start_seconds: float,
        end_seconds: float
    ) -> List[Dict[str, Any]]:
        """
        Get utterances within a specific time range.
        
        Args:
            meeting_id: Meeting UUID
            start_seconds: Start of time range
            end_seconds: End of time range
            
        Returns:
            List of utterance records
        """
        response = (
            self.table
            .select("*")
            .eq("meeting_id", str(meeting_id))
            .gte("start_seconds", start_seconds)
            .lte("end_seconds", end_seconds)
            .order("start_seconds", desc=False)
            .execute()
        )
        return response.data if response.data else []
    
    def get_full_transcript(
        self,
        meeting_id: str | UUID,
        include_timestamps: bool = True
    ) -> str:
        """
        Get full transcript as formatted text.
        
        Args:
            meeting_id: Meeting UUID
            include_timestamps: If True, include timestamps in output
            
        Returns:
            Formatted transcript string
        """
        utterances = self.get_utterances_by_meeting(meeting_id)
        
        if not utterances:
            return ""
        
        transcript_parts = []
        for utt in utterances:
            if include_timestamps:
                timestamp = f"[{utt['start_seconds']:.2f}s]"
                line = f"{timestamp} {utt['speaker']}: {utt['text']}"
            else:
                line = f"{utt['speaker']}: {utt['text']}"
            transcript_parts.append(line)
        
        return "\n".join(transcript_parts)
    
    def search_text(
        self,
        meeting_id: str | UUID,
        search_term: str,
        case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for utterances containing specific text.
        
        Args:
            meeting_id: Meeting UUID
            search_term: Text to search for
            case_sensitive: If True, perform case-sensitive search
            
        Returns:
            List of matching utterance records
        """
        query = (
            self.table
            .select("*")
            .eq("meeting_id", str(meeting_id))
        )
        
        if case_sensitive:
            query = query.like("text", f"%{search_term}%")
        else:
            query = query.ilike("text", f"%{search_term}%")
        
        response = query.order("start_seconds", desc=False).execute()
        return response.data if response.data else []
    
    def delete_utterances_by_meeting(self, meeting_id: str | UUID) -> bool:
        """
        Delete all utterances for a meeting.
        
        Args:
            meeting_id: Meeting UUID
            
        Returns:
            True if successful
        """
        response = (
            self.table
            .delete()
            .eq("meeting_id", str(meeting_id))
            .execute()
        )
        return len(response.data) > 0 if response.data else False

