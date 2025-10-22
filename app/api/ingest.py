# app/api/ingest.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, AnyUrl
import os
from sqlalchemy import text as sqltext
from app.utils.db import DB
from app.utils.asr_clients import start_asr_job

router = APIRouter(tags=["ingest"])

class IngestReq(BaseModel):
    meeting_id: str
    video_url: AnyUrl

def _ensure_meeting(con, meeting_id: str):
    # Creates a placeholder meeting row if it doesn't exist (prevents FK errors later)
    con.execute(sqltext("""
        INSERT INTO meetings (id, title, consent, status)
        VALUES (:id, 'Untitled', true, 'created')
        ON CONFLICT (id) DO NOTHING
    """), {"id": meeting_id})

@router.post("/ingest")
async def ingest(req: IngestReq):
    db = DB()
    with db.engine.begin() as con:
        _ensure_meeting(con, req.meeting_id)
        con.execute(sqltext("UPDATE meetings SET video_url=:u, status='asr_started' WHERE id=:id"),
                    {"u": str(req.video_url), "id": req.meeting_id})

    base = os.getenv("PUBLIC_API_BASE_URL", "")
    provider = os.getenv("ASR_PROVIDER", "assemblyai").lower()
    if provider not in {"assemblyai"}:
        raise HTTPException(400, f"Unsupported ASR_PROVIDER: {provider}")

    webhook_url = f"{base}/api/asr/webhook/{provider}" if base else None

    try:
        job_id = await start_asr_job(
            media_url=str(req.video_url),
            provider=provider,
            meeting_id=req.meeting_id,
            webhook_url=webhook_url,
        )
    except Exception as e:
        with db.engine.begin() as con:
            con.execute(sqltext("UPDATE meetings SET status='error' WHERE id=:id"),
                        {"id": req.meeting_id})
        raise HTTPException(500, f"ASR job start failed: {e}")

    # track job id
    try:
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO asr_jobs (job_id, meeting_id, provider, status, callback_url)
                VALUES (:jid, :m, :p, 'processing', :cb)
                ON CONFLICT (job_id) DO UPDATE
                  SET meeting_id=excluded.meeting_id,
                      provider=excluded.provider,
                      status=excluded.status,
                      callback_url=excluded.callback_url
            """), {"jid": job_id, "m": req.meeting_id, "p": provider, "cb": webhook_url})
    except Exception:
        pass

    return {"meeting_id": req.meeting_id, "status": "asr_started", "job_id": job_id}