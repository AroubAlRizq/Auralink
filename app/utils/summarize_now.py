# app/utils/summarize_now.py
from __future__ import annotations

import json
from typing import Dict, List
from sqlalchemy import text as sqltext
from sqlalchemy.exc import IntegrityError

from app.utils.db import DB
from app.rag.composer import summarize_meeting_json

try:
    from app.rag.indexer_service import index_summary
    HAS_INDEXER = True
except Exception:
    HAS_INDEXER = False


def _normalize_summary(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"overview": "", "key_points": [], "decisions": [], "action_items": []}

    exec_sum = payload.get("executive_summary")
    if isinstance(exec_sum, list):
        overview = " ".join([str(x).strip() for x in exec_sum if x])
    elif isinstance(exec_sum, str):
        overview = exec_sum.strip()
    else:
        overview = (payload.get("overview") or payload.get("raw_summary_text") or payload.get("summary") or "").strip()

    key_points = payload.get("key_points")
    if not isinstance(key_points, list):
        key_points = payload.get("key_events") if isinstance(payload.get("key_events"), list) else []

    decisions = payload.get("decisions") if isinstance(payload.get("decisions"), list) else []
    action_items = payload.get("action_items") if isinstance(payload.get("action_items"), list) else []
    return {"overview": overview, "key_points": key_points, "decisions": decisions, "action_items": action_items}


def _fetch_transcript(meeting_id: str) -> str:
    db = DB()
    with db.engine.begin() as con:
        rows = con.execute(sqltext("""
            SELECT speaker, start_seconds, end_seconds, text
            FROM utterances
            WHERE meeting_id = :m
            ORDER BY start_seconds
        """), {"m": meeting_id}).mappings().all()

    if not rows:
        return ""

    # Chunk very long transcripts to avoid model token limits
    # (Composer can still take the whole thing; keep it simple first.)
    transcript = "\n".join(
        f"[{r['start_seconds']:.1f}s {r['speaker']}] {r['text']}" for r in rows
    )
    return transcript


def summarize_now(meeting_id: str) -> dict:
    """
    Synchronously generates a summary for meeting_id from utterances and upserts it.
    Returns the normalized summary payload.
    """
    transcript = _fetch_transcript(meeting_id)
    if not transcript:
        # Nothing to do; caller should handle this message shown in UI.
        return {"overview": "", "key_points": [], "decisions": [], "action_items": []}

    # Call your LLM composer
    summary_raw = {}
    try:
        sr = summarize_meeting_json(transcript)
        # support async or sync composer
        if hasattr(sr, "__await__"):
            import anyio
            sr = anyio.run(lambda: sr)  # in case caller is sync
        summary_raw = sr or {}
    except Exception as e:
        summary_raw = {"raw_summary_text": f"[summary error] {e}"}

    if isinstance(summary_raw, dict):
        summary_raw["meeting_id"] = meeting_id

    normalized = _normalize_summary(summary_raw)

    # Upsert into summaries
    db = DB()
    try:
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO summaries (meeting_id, payload)
                VALUES (:m, CAST(:p AS jsonb))
                ON CONFLICT (meeting_id) DO UPDATE SET payload = CAST(:p AS jsonb)
            """), {"m": meeting_id, "p": json.dumps(summary_raw)})
    except IntegrityError:
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO meetings (id, title, consent, status)
                VALUES (:id, 'Untitled', true, 'created')
                ON CONFLICT (id) DO NOTHING
            """), {"id": meeting_id})
            con.execute(sqltext("""
                INSERT INTO summaries (meeting_id, payload)
                VALUES (:m, CAST(:p AS jsonb))
                ON CONFLICT (meeting_id) DO UPDATE SET payload = CAST(:p AS jsonb)
            """), {"m": meeting_id, "p": json.dumps(summary_raw)})

    if HAS_INDEXER:
        try:
            import anyio
            if anyio.current_effective_deadline() is not None:
                # already in async context
                import asyncio
                asyncio.create_task(index_summary(meeting_id, normalized))
            else:
                # best-effort fire-and-forget
                index_summary(meeting_id, normalized)  # type: ignore
        except Exception:
            pass

    # Mark status
    try:
        with db.engine.begin() as con:
            con.execute(sqltext("UPDATE meetings SET status='summary_ready' WHERE id=:m"), {"m": meeting_id})
    except Exception:
        pass

    return normalized