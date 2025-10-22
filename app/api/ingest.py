# app/api/ingest.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, AnyUrl
from sqlalchemy import text as sqltext
import os, asyncio, httpx

from app.utils.db import DB
from app.utils.asr_clients import start_asr_job

router = APIRouter(tags=["ingest"])
A2_BASE = "https://api.assemblyai.com/v2"

VERIFY_AAI_ON_CREATE = os.getenv("VERIFY_AAI_ON_CREATE", "0").lower() in {"1", "true", "yes"}

class IngestReq(BaseModel):
    meeting_id: str
    video_url: AnyUrl

def _ensure_meeting(con, meeting_id: str):
    con.execute(sqltext("""
        INSERT INTO meetings (id, title, consent, status)
        VALUES (:id, 'Untitled', true, 'created')
        ON CONFLICT (id) DO NOTHING
    """), {"id": meeting_id})

async def _verify_job_exists(job_id: str):
    """
    Verify transcript exists. Try plural first, then singular, with brief backoff.
    """
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")
    headers = {"Authorization": api_key}

    async def try_get(path: str) -> int:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{A2_BASE}/{path}", headers=headers)
        return r.status_code if r is not None else 599

    for delay in (0.5, 1.0, 2.0, 3.0):
        if delay:
            await asyncio.sleep(delay)
        sc = await try_get(f"transcripts/{job_id}")
        if sc == 200:
            return
        if sc not in (404, 500, 502, 503):
            raise HTTPException(502, f"Provider verify failed (plural): {sc}")
        if sc == 404:
            sc2 = await try_get(f"transcript/{job_id}")
            if sc2 == 200:
                return
            if sc2 not in (404, 500, 502, 503):
                raise HTTPException(502, f"Provider verify failed (singular): {sc2}")

    fp = api_key[-6:] if api_key else None
    raise HTTPException(502, f"Provider 404 for new job {job_id} (key FP {fp}). Check API key/env on server.")

@router.post("/ingest")
async def ingest(req: IngestReq):
    db = DB()
    with db.engine.begin() as con:
        _ensure_meeting(con, req.meeting_id)
        con.execute(sqltext("UPDATE meetings SET video_url=:u, status='asr_started' WHERE id=:id"),
                    {"u": str(req.video_url), "id": req.meeting_id})

    base = os.getenv("PUBLIC_API_BASE_URL", "").strip()
    provider = os.getenv("ASR_PROVIDER", "assemblyai").lower()
    if provider != "assemblyai":
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

    if VERIFY_AAI_ON_CREATE:
        await _verify_job_exists(job_id)

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

    aai_fp = (os.getenv("ASSEMBLYAI_API_KEY","") or "")[-6:]
    return {"meeting_id": req.meeting_id, "status": "asr_started", "job_id": job_id, "aai_fp": aai_fp}