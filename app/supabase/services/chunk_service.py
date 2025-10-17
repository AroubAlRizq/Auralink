# app/supabase/services/chunk_service.py
"""
Service class for Chunk model operations with Supabase.
Handles text chunks with embeddings for RAG/semantic search.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase import Client
from .base_service import BaseService


class ChunkService(BaseService):
    """
    Service for managing chunks (text segments with embeddings) in Supabase.
    Handles CRUD operations for the chunks table.
    """
    
    def __init__(self, client: Client):
        """Initialize ChunkService with Supabase client."""
        super().__init__(client, "chunks")
    
    def create_chunk(
        self,
        meeting_id: str | UUID,
        text: str,
        start_seconds: float,
        end_seconds: float,
        speaker: Optional[str] = None,
        topic: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Create a new chunk record.
        
        Args:
            meeting_id: Associated meeting UUID
            text: Text content of chunk
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            speaker: Speaker identifier (e.g., SPEAKER_0, WINDOW_0)
            topic: Topic/category (e.g., asr, multimodal_narration)
            embedding: Vector embedding (3072 dimensions for text-embedding-3-large)
            
        Returns:
            Created chunk record
        """
        data = {
            "meeting_id": str(meeting_id),
            "text": text,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "speaker": speaker,
            "topic": topic,
            "embedding": embedding
        }
        return self.create(data)
    
    def create_chunks_batch(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple chunks at once.
        
        Args:
            chunks: List of chunk data dictionaries
            
        Returns:
            List of created chunk records
        """
        return self.create_many(chunks)
    
    def get_chunks_by_meeting(
        self,
        meeting_id: str | UUID,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific meeting.
        
        Args:
            meeting_id: Meeting UUID
            limit: Maximum number of chunks to return
            
        Returns:
            List of chunk records ordered by start_seconds
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
    
    def get_chunks_by_time_range(
        self,
        meeting_id: str | UUID,
        start_seconds: float,
        end_seconds: float
    ) -> List[Dict[str, Any]]:
        """
        Get chunks within a specific time range.
        
        Args:
            meeting_id: Meeting UUID
            start_seconds: Start of time range
            end_seconds: End of time range
            
        Returns:
            List of chunk records
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
    
    def get_chunks_by_topic(
        self,
        meeting_id: str | UUID,
        topic: str
    ) -> List[Dict[str, Any]]:
        """
        Get chunks by topic/category.
        
        Args:
            meeting_id: Meeting UUID
            topic: Topic filter (e.g., asr, multimodal_narration)
            
        Returns:
            List of chunk records
        """
        response = (
            self.table
            .select("*")
            .eq("meeting_id", str(meeting_id))
            .eq("topic", topic)
            .order("start_seconds", desc=False)
            .execute()
        )
        return response.data if response.data else []
    
    def semantic_search(
        self,
        meeting_id: str | UUID,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity.
        
        Args:
            meeting_id: Meeting UUID
            query_embedding: Query vector embedding
            limit: Number of results to return
            
        Returns:
            List of most similar chunks
            
        Note:
            This uses pgvector's cosine similarity.
            Requires the embedding column to be indexed properly.
        """
        # Use RPC function for vector similarity search
        response = self.client.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "meeting_id": str(meeting_id),
                "match_count": limit
            }
        ).execute()
        
        return response.data if response.data else []
    
    def update_embedding(
        self,
        chunk_id: int,
        embedding: List[float]
    ) -> Dict[str, Any]:
        """
        Update the embedding for a chunk.
        
        Args:
            chunk_id: Chunk ID
            embedding: New vector embedding
            
        Returns:
            Updated chunk record
        """
        return self.update(chunk_id, {"embedding": embedding})
    
    def delete_chunks_by_meeting(self, meeting_id: str | UUID) -> bool:
        """
        Delete all chunks for a meeting.
        
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

