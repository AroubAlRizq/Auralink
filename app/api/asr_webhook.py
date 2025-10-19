# app/api/asr_webhook.py
from fastapi import APIRouter, Request, HTTPException
from ..utils.db import DB
import os
import time

router = APIRouter(tags=["webhooks"])

def _ms_to_s(v):
    try:
        return float(v) / 1000.0
    except Exception:
        return float(v)

@router.post("/asr/webhook/assemblyai")
async def assemblyai_webhook(req: Request):
    """
    Expected payload (simplified):
    {
      "id": "job_123",
      "status": "completed",
      "metadata": {"meeting_id": "..."},
      "utterances": [
        {"speaker": "A", "start": 1234, "end": 5678, "text": "..."},
        ...
      ],
      "error": "...optional..."
    }
    """
    payload = await req.json()
    status = payload.get("status")
    job_id = payload.get("id")
    metadata = payload.get("metadata") or {}
    meeting_id = metadata.get("meeting_id")

    db = DB()

    if status == "error":
        db.update_asr_job(job_id, status="error", error=str(payload.get("error")))
        raise HTTPException(500, f"ASR provider error: {payload.get('error')}")

    if status != "completed":
        # Provider may send intermediate events
        db.update_asr_job(job_id, status=status, raw=payload)
        return {"ok": True}

    # If meeting_id missing, try to map job to meeting
    if not meeting_id:
        meeting_id = db.meeting_id_from_job(job_id)
        if not meeting_id:
            raise HTTPException(400, "Missing meeting_id in metadata and no mapping found for job_id")

    # Normalize utterances
    ulist = []
    for u in payload.get("utterances", []):
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

    # Persist
    if ulist:
        db.bulk_insert_utterances(meeting_id, ulist)
    db.update_meeting_status(meeting_id, "asr_done")
    db.update_asr_job(job_id, status="completed", raw=payload)

    return {"ok": True, "meeting_id": meeting_id, "utterances": len(ulist)}

@router.post("/asr/webhook/deepgram")
async def deepgram_webhook(req: Request):
    """
    Deepgram callbacks vary; we try common shapes:
    - paragraphs/utterances with speaker, start, end, text
    """
    payload = await req.json()
    job_id = payload.get("request_id") or payload.get("id") or str(int(time.time()))
    meeting_id = None

    # Try metadata path
    md = payload.get("metadata") or {}
    meeting_id = md.get("meeting_id")

    # Possible locations of utterances
    utterances = []

    # v: payload["results"]["utterances"]
    try:
        for u in payload["results"]["utterances"]:
            if u.get("transcript"):
                utterances.append({
                    "speaker": u.get("speaker", "SPEAKER"),
                    "start_seconds": float(u.get("start", 0.0)),
                    "end_seconds": float(u.get("end", 0.0)),
                    "text": u["transcript"].strip()
                })
    except Exception:
        pass

    # Fallback: paragraphs
    if not utterances:
        try:
            paras = payload["results"]["channels"][0]["alternatives"][0]["paragraphs"]["paragraphs"]
            for p in paras:
                if p.get("transcript"):
                    utterances.append({
                        "speaker": p.get("speaker", "SPEAKER"),
                        "start_seconds": float(p.get("start", 0.0)),
                        "end_seconds": float(p.get("end", 0.0)),
                        "text": p["transcript"].strip()
                    })
        except Exception:
            pass

    db = DB()

    if not meeting_id:
        # Try to map job id
        meeting_id = db.meeting_id_from_job(job_id)
        if not meeting_id:
            raise HTTPException(400, "Missing meeting_id (metadata) and no mapping found for job_id")

    if utterances:
        db.bulk_insert_utterances(meeting_id, utterances)
    db.update_meeting_status(meeting_id, "asr_done")
    db.update_asr_job(job_id, status="completed", raw=payload)

    return {"ok": True, "meeting_id": meeting_id, "utterances": len(utterances)}
