# app/api/aai_poll.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text as sqltext
import os, httpx, json

from app.utils.db import DB
from app.utils.summarize_now import summarize_now

router = APIRouter(tags=["asr"])

A2_BASE = "https://api.assemblyai.com/v2"

class PollReq(BaseModel):
    job_id: str

def _ms_to_s(v):
    try:
        return float(v) / 1000.0
    except Exception:
        try:
            return float(v)
        except Exception:
            return 0.0

@router.post("/aai/poll")
async def aai_poll(req: PollReq):
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")

    headers = {"Authorization": api_key}

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.get(f"{A2_BASE}/transcripts/{req.job_id}", headers=headers)
        if r.status_code == 404:
            return {"status": "not_found", "phase": "not_found", "job_id": req.job_id}
        if r.status_code >= 400:
            raise HTTPException(502, f"AAI poll failed: {r.status_code}: {r.text}")
        data = r.json()

    # Persist raw/status for inspection
    db = DB()
    with db.engine.begin() as con:
        con.execute(text("""
            UPDATE asr_jobs SET status=:s, raw=CAST(:raw AS jsonb)
            WHERE job_id=:id
        """), {"s": data.get("status"), "id": req.job_id, "raw": json.dumps(data)})

    status = (data.get("status") or "").lower()
    phase = "queued" if status in {"queued"} else (
        "processing" if status in {"processing"} else (
            "completed" if status == "completed" else (
                "error" if status in {"error", "failed"} else status or "unknown"
            )
        )
    )

    audio_dur = float(data.get("audio_duration") or 0.0)  # seconds
    words = data.get("words") or []
    last_end_s = _ms_to_s(words[-1].get("end")) if words else 0.0
    progress = 1.0 if phase == "completed" else (min(0.99, last_end_s / audio_dur) if audio_dur > 0 else 0.0)

    # Early return for non-completed
    if phase != "completed":
        return {
            "status": status,
            "phase": phase,
            "job_id": req.job_id,
            "progress": progress,
            "audio_duration": audio_dur,
            "provider_error": data.get("error") or None,
            "confidence": data.get("confidence"),
        }

    # Completed: persist utterances and summarize (same as before)
    with db.engine.begin() as con:
        row = con.execute(text("SELECT meeting_id FROM asr_jobs WHERE job_id=:id"),
                          {"id": req.job_id}).first()
    meeting_id = row[0] if row else None

    utterances = data.get("utterances") or data.get("sentences") or []
    if not utterances and (data.get("text") or words):
        text_all = data.get("text", "") or "[no text from ASR]"
        start_s = _ms_to_s(words[0].get("start")) if words else 0.0
        end_s = _ms_to_s(words[-1].get("end")) if words else 0.0
        utterances = [{"speaker": "Speaker 1", "start": start_s * 1000, "end": end_s * 1000, "text": text_all}]

    saved = 0
    if meeting_id:
        with db.engine.begin() as con:
            con.execute(text("DELETE FROM utterances WHERE meeting_id=:m"), {"m": meeting_id})
            for u in utterances:
                con.execute(text("""
                    INSERT INTO utterances (meeting_id, speaker, start_seconds, end_seconds, text)
                    VALUES (:m, :spk, :ss, :es, :txt)
                """), {
                    "m": meeting_id,
                    "spk": u.get("speaker") or u.get("speaker_label") or "Speaker",
                    "ss": _ms_to_s(u.get("start", 0)),
                    "es": _ms_to_s(u.get("end", 0)),
                    "txt": (u.get("text") or "").strip(),
                })
                saved += 1
            con.execute(text("UPDATE meetings SET status='asr_done' WHERE id=:m"), {"m": meeting_id})

    summary_ready = False
    if meeting_id:
        summary = summarize_now(meeting_id)
        summary_ready = bool(
            summary.get("overview")
            or summary.get("key_points")
            or summary.get("decisions")
            or summary.get("action_items")
        )

    return {
        "status": status,
        "phase": phase,
        "job_id": req.job_id,
        "meeting_id": meeting_id,
        "saved": saved,
        "progress": 1.0,
        "audio_duration": audio_dur,
        "summary_ready": summary_ready,
        "provider_error": data.get("error") or None,
        "confidence": data.get("confidence"),
    }