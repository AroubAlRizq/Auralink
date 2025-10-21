# app/api/ingest.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
import shutil
from pydantic import BaseModel, HttpUrl
import os
from app.utils.database import DatabaseManager
from app.utils.asr_clients import start_asr_job

router = APIRouter(tags=["ingest"])

class IngestReq(BaseModel):
    meeting_id: str
    video_url: HttpUrl

@router.post("/ingest")
async def ingest(req: IngestReq):
    """
    Store the video URL for a meeting and kick off ASR.
    The ASR provider will call /api/asr/webhook/<provider> when done.
    """
    db = DatabaseManager()

    # Save/Update video_url and mark status
    try:
        db.set_meeting_video_url(req.meeting_id, str(req.video_url))
        db.update_meeting_status(req.meeting_id, "asr_started")
    except Exception as e:
        raise HTTPException(400, f"Failed to update meeting: {e}")

    # Build webhook URL (publicly reachable)
    base = os.getenv("PUBLIC_API_BASE_URL", "")
    provider = os.getenv("ASR_PROVIDER", "assemblyai").lower()
    
    if provider not in {"assemblyai", "deepgram"}:
        raise HTTPException(400, f"Unsupported ASR_PROVIDER: {provider}")

    webhook_url = f"{base}/api/asr/webhook/{provider}" if base else None

    # Start job at provider (include meeting_id in metadata)
    try:
        job_id = await start_asr_job(
            media_url=str(req.video_url),
            provider=provider,
            meeting_id=req.meeting_id,
            webhook_url=webhook_url,
        )
    except Exception as e:
        db.update_meeting_status(req.meeting_id, "error")
        raise HTTPException(500, f"ASR job start failed: {e}")

    # Track job
    try:
        db.upsert_asr_job(
            job_id=job_id,
            meeting_id=req.meeting_id,
            provider=provider,
            status="processing",
            callback_url=webhook_url
        )
    except Exception as e:
        print(f"Warning: Failed to track ASR job: {e}")

    return {
        "meeting_id": req.meeting_id,
        "status": "asr_started",
        "job_id": job_id
    }

@router.post("/ingest/upload")
async def ingest_upload(
    meeting_id: str = Form(...),
    video_file: UploadFile = File(...)
):
    """
    Upload a video file directly instead of providing a URL.
    Creates a new meeting if meeting_id is 'new', otherwise uses provided UUID.
    """
    db = DatabaseManager()
    
    # Create new meeting if requested
    if meeting_id.lower() == "new":
        meeting_id = db.create_meeting(
            title=video_file.filename or "Uploaded Meeting",
            consent=True
        )
        print(f"✅ Created new meeting: {meeting_id}")
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    file_ext = Path(video_file.filename).suffix
    file_path = upload_dir / f"{meeting_id}{file_ext}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
    except Exception as e:
        # Clean up failed meeting if we just created it
        raise HTTPException(500, f"Failed to save file: {e}")
    
    # Store file path as URL in database
    video_url = str(file_path.absolute())
    
    # Save to database
    try:
        db.set_meeting_video_url(meeting_id, video_url)
        db.update_meeting_status(meeting_id, "asr_started")
    except Exception as e:
        raise HTTPException(400, f"Failed to update meeting: {e}")
    
    # Prepare ASR job
    base = os.getenv("PUBLIC_API_BASE_URL", "")
    provider = os.getenv("ASR_PROVIDER", "assemblyai").lower()
    
    if provider not in {"assemblyai", "deepgram"}:
        raise HTTPException(400, f"Unsupported ASR_PROVIDER: {provider}")
    
    webhook_url = f"{base}/api/asr/webhook/{provider}" if base else None
    
    # Start ASR job with local file
    try:
        job_id = await start_asr_job(
            media_url=str(file_path.absolute()),
            provider=provider,
            meeting_id=meeting_id,
            webhook_url=webhook_url,
        )
    except Exception as e:
        db.update_meeting_status(meeting_id, "error")
        raise HTTPException(500, f"ASR job start failed: {e}")
    
    # Track job
    try:
        db.upsert_asr_job(
            job_id=job_id,
            meeting_id=meeting_id,
            provider=provider,
            status="processing",
            callback_url=webhook_url
        )
    except Exception as e:
        print(f"Warning: Failed to track ASR job: {e}")
    
    return {
        "meeting_id": meeting_id,
        "status": "asr_started",
        "job_id": job_id,
        "file_path": str(file_path),
        "filename": video_file.filename,
        "content_type": video_file.content_type
    }