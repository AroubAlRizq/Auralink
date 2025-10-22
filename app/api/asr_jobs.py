# app/api/asr_jobs.py
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text as sqltext
from app.utils.db import DB

router = APIRouter(tags=["asr"])

@router.get("/asr/job_for_meeting")
def job_for_meeting(meeting_id: str = Query(...)):
    db = DB()
    with db.engine.begin() as con:
        row = con.execute(sqltext("""
            SELECT job_id, provider, status, callback_url
            FROM asr_jobs
            WHERE meeting_id = :m
            ORDER BY created_at DESC NULLS LAST
            LIMIT 1
        """), {"m": meeting_id}).mappings().first()
    if not row:
        raise HTTPException(404, "No ASR job found for this meeting_id")
    return dict(row)