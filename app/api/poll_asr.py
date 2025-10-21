# app/api/poll_asr.py
"""
Endpoint to manually poll ASR status when webhook is not available.
Use this for local development without ngrok.
"""

from fastapi import APIRouter, HTTPException, Query
import httpx
import os
from app.utils.database import DatabaseManager
from app.rag.indexer_service import index_transcript

router = APIRouter(tags=["polling"])

def _ms_to_s(v):
    """Convert milliseconds to seconds"""
    try:
        return float(v) / 1000.0
    except Exception:
        return float(v)

@router.post("/poll/asr/{meeting_id}")
async def poll_asr_status(meeting_id: str):
    """
    Manually poll AssemblyAI for the status of a transcription job.
    Use this when you don't have a public webhook URL (local development).
    
    This will:
    1. Find the ASR job for this meeting
    2. Check its status with AssemblyAI
    3. If complete, download and process the transcript
    4. Auto-index for RAG
    """
    
    db = DatabaseManager()
    
    # Get the ASR job for this meeting
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    cur.execute("""
        SELECT job_id, provider, status 
        FROM asr_jobs 
        WHERE meeting_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (meeting_id,))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if not result:
        raise HTTPException(404, f"No ASR job found for meeting {meeting_id}")
    
    job_id, provider, current_status = result
    
    if provider != "assemblyai":
        raise HTTPException(400, f"Polling only supported for AssemblyAI (this job uses {provider})")
    
    if current_status == "completed":
        return {
            "status": "completed",
            "message": "Transcript already processed",
            "meeting_id": meeting_id
        }
    
    # Poll AssemblyAI
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not configured")
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"https://api.assemblyai.com/v2/transcript/{job_id}",
            headers={"authorization": api_key}
        )
        response.raise_for_status()
        data = response.json()
    
    status = data.get("status")
    
    # Update job status
    db.update_asr_job(job_id, status=status, raw=data)
    
    if status == "error":
        error_msg = data.get("error", "Unknown error")
        db.update_meeting_status(meeting_id, "error")
        raise HTTPException(500, f"ASR failed: {error_msg}")
    
    if status == "queued" or status == "processing":
        return {
            "status": status,
            "message": f"Transcript is still {status}. Poll again in 30 seconds.",
            "meeting_id": meeting_id,
            "job_id": job_id
        }
    
    if status == "completed":
        # Process the transcript
        ulist = []
        for u in data.get("utterances", []):
            sp = u.get("speaker") or "SPEAKER"
            start = _ms_to_s(u.get("start", 0))
            end = _ms_to_s(u.get("end", start))
            text = (u.get("text") or "").strip()
            if text:
                ulist.append({
                    "speaker": sp,
                    "start_seconds": start,
                    "end_seconds": end,
                    "text": text
                })
        
        # Save utterances
        if ulist:
            db.bulk_insert_utterances(meeting_id, ulist)
        
        db.update_meeting_status(meeting_id, "asr_done")
        db.update_asr_job(job_id, status="completed", raw=data)
        
        # Auto-index
        indexed = 0
        try:
            indexed = await index_transcript(meeting_id, ulist)
        except Exception as e:
            print(f"Indexing failed: {e}")
        
        return {
            "status": "completed",
            "message": "Transcript processed successfully!",
            "meeting_id": meeting_id,
            "utterances": len(ulist),
            "indexed_chunks": indexed
        }
    
    return {
        "status": status,
        "message": f"Unknown status: {status}",
        "meeting_id": meeting_id
    }

@router.get("/poll/asr/{meeting_id}/status")
async def get_asr_status(meeting_id: str):
    """
    Quick status check without processing.
    Returns the current status from the database.
    """
    db = DatabaseManager()
    
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    cur.execute("""
        SELECT job_id, provider, status, created_at
        FROM asr_jobs 
        WHERE meeting_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (meeting_id,))
    
    result = cur.fetchone()
    
    if not result:
        cur.close()
        conn.close()
        raise HTTPException(404, f"No ASR job found for meeting {meeting_id}")
    
    job_id, provider, status, created_at = result
    
    # Also get meeting status
    cur.execute("SELECT status FROM meetings WHERE id = %s", (meeting_id,))
    meeting_result = cur.fetchone()
    meeting_status = meeting_result[0] if meeting_result else "unknown"
    
    cur.close()
    conn.close()
    
    return {
        "meeting_id": meeting_id,
        "meeting_status": meeting_status,
        "asr_job_id": job_id,
        "asr_provider": provider,
        "asr_status": status,
        "created_at": created_at,
        "instructions": {
            "if_processing": f"Run: curl -X POST http://localhost:8000/api/poll/asr/{meeting_id}",
            "if_completed": f"Generate summary: curl -X POST http://localhost:8000/api/summarize?mode=text&meeting_id={meeting_id}"
        }
    }