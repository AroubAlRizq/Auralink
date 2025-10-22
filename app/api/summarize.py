# app/api/summarize.py
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text as sqltext
from sqlalchemy.exc import IntegrityError
import os, json, asyncio
import httpx

from app.rag.composer import summarize_meeting_json
from app.utils.db import DB

try:
    from app.rag.indexer_service import index_summary
    HAS_INDEXER = True
except Exception:
    HAS_INDEXER = False

router = APIRouter(tags=["summarize"])

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

async def _summarize_with_retries(transcript: str, attempts=(0.5, 1.0, 2.0, 4.0)):
    """
    Call summarize_meeting_json with small exponential backoff on rate limits (429) and transient 5xx.
    Returns a dict payload (may be empty on final failure).
    """
    last_err = None
    for i, delay in enumerate(attempts, 1):
        try:
            return await summarize_meeting_json(transcript)  # composer is async
        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response else None
            if code in (429, 500, 502, 503):
                last_err = f"{code}: {e}"
                await asyncio.sleep(delay)
                continue
            # non-retryable error
            raise
        except Exception as e:
            # network/timeout → retry
            last_err = str(e)
            await asyncio.sleep(delay)
            continue
    # give up
    return {"raw_summary_text": f"[summary unavailable after retries] {last_err or ''}".strip()}

@router.post("/summarize")
async def summarize(
    mode: str = Query("text", pattern="^(text)$"),
    meeting_id: str | None = Query(None),
):
    if not meeting_id:
        raise HTTPException(400, "meeting_id is required.")

    db = DB()
    # Build transcript from utterances
    with db.engine.begin() as con:
        rows = con.execute(sqltext("""
            SELECT speaker, start_seconds, end_seconds, text
            FROM utterances
            WHERE meeting_id = :m
            ORDER BY start_seconds
        """), {"m": meeting_id}).mappings().all()

    if not rows:
        raise HTTPException(409, "No utterances found for this meeting_id. Run ingest/transcription first.")

    transcript = "\n".join(
        f"[{r['start_seconds']:.1f}s {r['speaker']}] {r['text']}" for r in rows
    )

    # 🔁 Retry on 429/5xx so we don't crash the endpoint
    try:
        summary_raw = await _summarize_with_retries(transcript)
    except httpx.HTTPStatusError as e:
        # If something non-retryable bubbles up, return a clear error to the UI
        code = e.response.status_code if e.response else 500
        raise HTTPException(code, f"Summarization failed: {e}")

    if isinstance(summary_raw, dict):
        summary_raw["meeting_id"] = meeting_id
    normalized = _normalize_summary(summary_raw)

    # Upsert into summaries; if FK fails, auto-create meeting row and retry
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
            await index_summary(meeting_id, normalized)
        except Exception:
            pass

    # Best-effort status bump
    try:
        with db.engine.begin() as con:
            con.execute(sqltext("UPDATE meetings SET status='summary_ready' WHERE id=:m"), {"m": meeting_id})
    except Exception:
        pass

    return normalized