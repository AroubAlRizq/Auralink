# app/utils/database.py
from typing import List, Optional
import logging
import json
import uuid
from .supabase_client import supabase

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.client = supabase
    
    # ==================== MEETINGS ====================
    def create_meeting(self, title: str, consent: bool) -> str:
        """Create a new meeting and return its UUID"""
        query = """
            INSERT INTO meetings (title, consent, status)
            VALUES (%s, %s, 'pending')
            RETURNING id
        """
        result = self.client.execute_query(query, (title, consent))
        meeting_id = str(result[0][0]) if result else None
        logger.info(f"Created meeting with ID: {meeting_id}")
        return meeting_id
    
    def set_meeting_video_url(self, meeting_id: str, video_url: str) -> bool:
        """Update meeting video URL"""
        query = "UPDATE meetings SET video_url = %s WHERE id = %s"
        try:
            self.client.execute_query(query, (video_url, meeting_id))
            logger.info(f"Updated video URL for meeting {meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update video URL: {e}")
            return False
    
    def update_meeting_status(self, meeting_id: str, status: str) -> bool:
        """Update meeting status"""
        query = "UPDATE meetings SET status = %s WHERE id = %s"
        try:
            self.client.execute_query(query, (status, meeting_id))
            logger.info(f"Updated status to '{status}' for meeting {meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update meeting status: {e}")
            return False
    
    def get_meeting(self, meeting_id: str) -> Optional[dict]:
        """Get meeting by ID"""
        query = "SELECT id, title, created_at, video_url, status FROM meetings WHERE id = %s"
        result = self.client.execute_query(query, (meeting_id,))
        
        if result and result[0]:
            row = result[0]
            return {
                "id": str(row[0]),
                "title": row[1],
                "created_at": row[2],
                "video_url": row[3],
                "status": row[4]
            }
        return None
    
    # ==================== UTTERANCES ====================
    def bulk_insert_utterances(self, meeting_id: str, utterances: List[dict]) -> bool:
        """Bulk insert utterances for a meeting"""
        if not utterances:
            return True
        
        query = """
            INSERT INTO utterances (meeting_id, speaker, start_seconds, end_seconds, text)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            conn = self.client.get_connection()
            with conn.cursor() as cursor:
                for utterance in utterances:
                    cursor.execute(
                        query,
                        (
                            meeting_id,
                            utterance["speaker"],
                            utterance["start_seconds"],
                            utterance["end_seconds"],
                            utterance["text"]
                        )
                    )
            logger.info(f"Inserted {len(utterances)} utterances for meeting {meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert utterances: {e}")
            return False
    
    def get_utterances_by_meeting(self, meeting_id: str) -> List[dict]:
        """Get all utterances for a meeting"""
        query = """
            SELECT id, meeting_id, speaker, start_seconds, end_seconds, text, created_at
            FROM utterances 
            WHERE meeting_id = %s 
            ORDER BY start_seconds
        """
        result = self.client.execute_query(query, (meeting_id,))
        
        utterances = []
        for row in result or []:
            utterances.append({
                "id": row[0],
                "meeting_id": str(row[1]),
                "speaker": row[2],
                "start_seconds": row[3],
                "end_seconds": row[4],
                "text": row[5],
                "created_at": row[6]
            })
        return utterances
    
    # ==================== ASR JOBS ====================
    def upsert_asr_job(
        self, 
        job_id: str,
        meeting_id: str,
        provider: str,
        status: str,
        callback_url: str = None,
        raw: dict = None,
        error: str = None
    ) -> bool:
        """Insert or update ASR job"""
        query = """
            INSERT INTO asr_jobs (job_id, meeting_id, provider, status, callback_url, raw, error)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (job_id) DO UPDATE SET
                meeting_id = EXCLUDED.meeting_id,
                provider = EXCLUDED.provider,
                status = EXCLUDED.status,
                callback_url = EXCLUDED.callback_url,
                raw = EXCLUDED.raw,
                error = EXCLUDED.error,
                updated_at = NOW()
        """
        
        try:
            raw_json = json.dumps(raw) if raw else None
            self.client.execute_query(
                query,
                (job_id, meeting_id, provider, status, callback_url, raw_json, error)
            )
            logger.info(f"Upserted ASR job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert ASR job: {e}")
            return False
    
    def update_asr_job(self, job_id: str, status: str, raw=None, error: str = None) -> bool:
        """Update ASR job status and data"""
        query = """
            UPDATE asr_jobs
            SET status = %s,
                raw = COALESCE(%s::jsonb, raw),
                error = COALESCE(%s, error),
                updated_at = NOW()
            WHERE job_id = %s
        """
        
        try:
            raw_json = json.dumps(raw) if raw else None
            self.client.execute_query(query, (status, raw_json, error, job_id))
            logger.info(f"Updated ASR job {job_id} to status: {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update ASR job: {e}")
            return False
    
    def meeting_id_from_job(self, job_id: str) -> Optional[str]:
        """Get meeting ID associated with an ASR job"""
        query = "SELECT meeting_id FROM asr_jobs WHERE job_id = %s"
        result = self.client.execute_query(query, (job_id,))
        return str(result[0][0]) if result and result[0] else None
    
    def get_asr_job(self, job_id: str) -> Optional[dict]:
        """Get ASR job by ID"""
        query = "SELECT * FROM asr_jobs WHERE job_id = %s"
        result = self.client.execute_query(query, (job_id,))
        
        if result and result[0]:
            row = result[0]
            return {
                "job_id": row[0],
                "meeting_id": str(row[1]),
                "provider": row[2],
                "status": row[3],
                "callback_url": row[4],
                "raw": row[5],
                "error": row[6],
                "created_at": row[7],
                "updated_at": row[8]
            }
        return None
    
    # ==================== SUMMARIES ====================
    def upsert_summary(self, meeting_id: str, payload: dict) -> bool:
        """Insert or update meeting summary"""
        query = """
            INSERT INTO summaries (meeting_id, payload)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (meeting_id) DO UPDATE SET 
                payload = EXCLUDED.payload,
                created_at = NOW()
        """
        try:
            self.client.execute_query(query, (meeting_id, json.dumps(payload)))
            logger.info(f"Upserted summary for meeting {meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert summary: {e}")
            return False
    
    def get_summary(self, meeting_id: str) -> Optional[dict]:
        """Get summary for a meeting"""
        query = "SELECT payload FROM summaries WHERE meeting_id = %s"
        result = self.client.execute_query(query, (meeting_id,))
        return result[0][0] if result and result[0] else None

# Global instance
db = DatabaseManager()