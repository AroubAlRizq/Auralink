# app/api/ingest_file.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy import text as sqltext
import os
import httpx

from app.utils.db import DB

router = APIRouter(tags=["ingest"])

A2_BASE = "https://api.assemblyai.com/v2"
AAI_400_SCHEMA_MSG = "Invalid endpoint schema"

def _headers():
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")
    # NOTE: JSON headers are only for POST /transcript(s) calls, not for /upload
    return {
        "Authorization": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

async def _aai_upload(file: UploadFile) -> str:
    """Stream the uploaded file to AssemblyAI /upload and return the upload_url."""
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")

    async def gen():
        while True:
            chunk = await file.read(5 * 1024 * 1024)  # 5MB
            if not chunk:
                break
            yield chunk

    # IMPORTANT: /upload requires ONLY the Authorization header; no JSON content-type
    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.post(
            f"{A2_BASE}/upload",
            headers={"Authorization": api_key},
            content=gen(),
        )
    if r.status_code >= 400:
        raise HTTPException(502, f"AssemblyAI upload failed: {r.status_code} {r.text}")

    try:
        data = r.json()
    except Exception:
        raise HTTPException(502, f"AssemblyAI upload returned non-JSON: {r.text[:200]}")

    url = data.get("upload_url")
    if not url:
        raise HTTPException(502, f"AssemblyAI missing upload_url: {data}")
    return url

async def _post_transcript(json_payload: dict, *, endpoint: str = "transcript"):
    """POST to /v2/<endpoint> with the given JSON payload. Returns (status, text, json|None)."""
    url = f"{A2_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=_headers(), json=json_payload)
    try:
        data = r.json()
    except Exception:
        data = None
    return r.status_code, r.text, data

def _ensure_meeting(con, meeting_id: str):
    con.execute(sqltext("""
        INSERT INTO meetings (id, title, consent, status)
        VALUES (:id, 'Untitled', true, 'created')
        ON CONFLICT (id) DO NOTHING
    """), {"id": meeting_id})

@router.post("/ingest_file")
async def ingest_file(
    meeting_id: str = Form(...),
    video_file: UploadFile = File(...),
):
    """
    Accept a local file, upload to AssemblyAI, start a transcript job,
    and persist job ↔ meeting mapping. Mirrors /ingest (URL) behavior.
    """
    db = DB()

    # 1) Make sure the meeting row exists, set status
    with db.engine.begin() as con:
        _ensure_meeting(con, meeting_id)
        con.execute(
            sqltext("UPDATE meetings SET video_url=:u, status='asr_started' WHERE id=:id"),
            {"u": f"uploaded://{video_file.filename}", "id": meeting_id},
        )

    # 2) Upload the media to AssemblyAI
    upload_url = await _aai_upload(video_file)

    # 3) Build webhook URL if PUBLIC_API_BASE_URL is set and HTTPS (required by AAI)
    base = os.getenv("PUBLIC_API_BASE_URL", "").strip()
    webhook_url = f"{base}/api/asr/webhook/assemblyai" if base.startswith("https://") else None

    # 4) Start the transcript job with adaptive retries (like /ingest)
    payload_standard = {
        "audio_url": upload_url,
        "speaker_labels": True,
        # AAI requires metadata to be a STRING; use meeting_id so your webhook can map it back
        "metadata": str(meeting_id),
    }
    if webhook_url:
        payload_standard["webhook_url"] = webhook_url

    status, text, data = await _post_transcript(payload_standard, endpoint="transcript")
    if status < 400 and isinstance(data, dict) and data.get("id"):
        job_id = data["id"]
    else:
        # If not a schema error, fail with details
        if status >= 400 and AAI_400_SCHEMA_MSG not in text:
            raise HTTPException(502, f"AssemblyAI create transcript failed: {status} {text}")

        # Minimal retry
        payload_min = {"audio_url": upload_url}
        if webhook_url:
            payload_min["webhook_url"] = webhook_url

        status, text, data = await _post_transcript(payload_min, endpoint="transcript")
        if status < 400 and isinstance(data, dict) and data.get("id"):
            job_id = data["id"]
        else:
            # Try plural endpoint as a last resort
            status, text, data = await _post_transcript(payload_min, endpoint="transcripts")
            if status < 400 and isinstance(data, dict) and data.get("id"):
                job_id = data["id"]
            else:
                raise HTTPException(502, f"AssemblyAI create transcript failed: {status} {text}")

    # 5) Track job row (same structure as /ingest)
    try:
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO asr_jobs (job_id, meeting_id, provider, status, callback_url)
                VALUES (:jid, :m, 'assemblyai', 'processing', :cb)
                ON CONFLICT (job_id) DO UPDATE
                  SET meeting_id=excluded.meeting_id,
                      provider=excluded.provider,
                      status=excluded.status,
                      callback_url=excluded.callback_url
            """), {"jid": job_id, "m": meeting_id, "cb": webhook_url})
    except Exception:
        # non-fatal; polling will still work
        pass

    return {"meeting_id": meeting_id, "status": "asr_started", "job_id": job_id}