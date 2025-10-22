# app/api/utterances.py
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text as sqltext
from app.utils.db import DB

router = APIRouter(tags=["utterances"])

@router.get("/utterances")
def list_utterances(meeting_id: str = Query(...)):
    db = DB()
    with db.engine.begin() as con:
        rows = con.execute(sqltext("""
            SELECT speaker, start_seconds, end_seconds, text
            FROM utterances
            WHERE meeting_id = :m
            ORDER BY start_seconds
        """), {"m": meeting_id}).mappings().all()
    return {"meeting_id": meeting_id, "utterances": list(rows)}