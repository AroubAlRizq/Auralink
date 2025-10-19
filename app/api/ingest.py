
# app/api/ingest.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, AnyUrl
import os
from app.utils.db import DB
from app.utils.asr_clients import start_asr_job

router = APIRouter(tags=["ingest"])

class IngestReq(BaseModel):
    meeting_id: str
    video_url: AnyUrl

@router.post("/ingest")
async def ingest(req: IngestReq):
    """
    Store the video URL for a meeting and kick off ASR.
    The ASR provider will call /api/asr/webhook/<provider> when done.
    """
    db = DB()

    # Save/Update video_url and mark status
    try:
        db.set_meeting_video_url(req.meeting_id, str(req.video_url))
        db.update_meeting_status(req.meeting_id, "asr_started")
    except Exception as e:
        raise HTTPException(400, f"Failed to update meeting: {e}")

    # Build webhook URL (publicly reachable)
    base = os.getenv("PUBLIC_API_BASE_URL")  # e.g., https://your-api.example.com
    if not base:
        # fallback to relative path if behind the same domain (not ideal for providers)
        base = ""
    provider = os.getenv("ASR_PROVIDER", "assemblyai").lower()
    if provider not in {"assemblyai", "deepgram"}:
        raise HTTPException(400, f"Unsupported ASR_PROVIDER: {provider}")

    webhook_url = f"{base}/api/asr/webhook/{provider}" if base else f"/api/asr/webhook/{provider}"

    # Start job at provider (include meeting_id in metadata when possible)
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
            callback_url=webhook_url,
        )
    except Exception:
        pass  # non-fatal

    return {"meeting_id": req.meeting_id, "status": "asr_started", "job_id": job_id}
