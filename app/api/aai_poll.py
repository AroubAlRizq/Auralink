# app/api/aai_poll.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text as sqltext
import os, asyncio, json, httpx

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

async def _provider_get(headers, path):
    async with httpx.AsyncClient(timeout=45) as client:
        return await client.get(f"{A2_BASE}/{path}", headers=headers)

@router.post("/aai/poll")
async def aai_poll(req: PollReq):
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")
    headers = {"Authorization": api_key}

    # Try plural first, fallback to singular, with short retries (≤ ~20s total)
    last = None
    for delay in (0, 1.0, 2.0, 4.0, 8.0):
        if delay:
            await asyncio.sleep(delay)
        r = await _provider_get(headers, f"transcripts/{req.job_id}")
        last = r
        if r.status_code == 200:
            break
        if r.status_code == 404:
            r2 = await _provider_get(headers, f"transcript/{req.job_id}")
            last = r2
            if r2.status_code == 200:
                r = r2
                break
        if r.status_code not in (404, 500, 502, 503):
            raise HTTPException(502, f"AAI poll failed: {r.status_code}: {r.text}")

    if not last or last.status_code == 404:
        return {
            "status": "not_found",
            "phase": "not_found",
            "job_id": req.job_id,
            "api_key_fingerprint": api_key[-6:] if api_key else None,
        }
    if last.status_code >= 400:
        raise HTTPException(502, f"AAI poll failed: {last.status_code}: {last.text}")

    data = last.json()
    status = (data.get("status") or "").lower()

    # persist job status
    from app.utils.db import DB
    db = DB()
    with db.engine.begin() as con:
        con.execute(sqltext("""
            UPDATE asr_jobs SET status=:s, raw=CAST(:raw AS jsonb)
            WHERE job_id=:id
        """), {"s": status, "id": req.job_id, "raw": json.dumps(data)})

    phase = (
        "queued" if status == "queued" else
        "processing" if status == "processing" else
        "completed" if status == "completed" else
        "error" if status in {"error", "failed"} else status
    )
    audio_dur = float(data.get("audio_duration") or 0.0)
    words = data.get("words") or []
    last_end_s = _ms_to_s(words[-1].get("end")) if words else 0.0
    progress = 1.0 if phase == "completed" else (min(0.99, last_end_s / audio_dur) if audio_dur > 0 else 0.0)

    if phase != "completed":
        return {
            "status": status,
            "phase": phase,
            "job_id": req.job_id,
            "progress": progress,
            "audio_duration": audio_dur,
            "provider_error": data.get("error") or None,
        }

    # Completed: map to utterances and persist
    with db.engine.begin() as con:
        row = con.execute(sqltext("SELECT meeting_id FROM asr_jobs WHERE job_id=:id"), {"id": req.job_id}).first()
    meeting_id = row[0] if row else None

    utterances = data.get("utterances") or data.get("sentences") or []
    if not utterances and (data.get("text") or words):
        text_all = data.get("text", "") or "[no text from ASR]"
        start_s = _ms_to_s(words[0].get("start")) if words else 0.0
        end_s = _ms_to_s(words[-1].get("end")) if words else 0.0
        utterances = [{
            "speaker": "Speaker 1",
            "start": start_s * 1000,
            "end": end_s * 1000,
            "text": text_all
        }]

    saved = 0
    if meeting_id:
        with db.engine.begin() as con:
            con.execute(sqltext("DELETE FROM utterances WHERE meeting_id=:m"), {"m": meeting_id})
            for u in utterances:
                con.execute(sqltext("""
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
            con.execute(sqltext("UPDATE meetings SET status='asr_done' WHERE id=:m"), {"m": meeting_id})

    # ✅ Best-effort summary inline using sync helper (no await!)
    summary_ready = False
    try:
        from app.utils.summarize_now import summarize_now
        if meeting_id:
            summary = summarize_now(meeting_id)
            summary_ready = bool(
                summary.get("overview") or
                summary.get("key_points") or
                summary.get("decisions") or
                summary.get("action_items")
            )
    except Exception:
        summary_ready = False

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
    }