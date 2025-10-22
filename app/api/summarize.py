# app/api/summarize.py
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text as sqltext
from sqlalchemy.exc import IntegrityError
import os, json

from app.rag.composer import summarize_meeting_json
from app.utils.db import DB

try:
    from app.rag.indexer_service import index_summary
    HAS_INDEXER = True
except Exception:
    HAS_INDEXER = False

# --- Optional: only used if you want a fallback without utterances
USE_GEMINI_FALLBACK = os.getenv("USE_GEMINI_FALLBACK", "false").lower() in {"1","true","yes"}
if USE_GEMINI_FALLBACK:
    try:
        from app.models.video_audio_summarizer import summarize_video
    except Exception:
        summarize_video = None
        USE_GEMINI_FALLBACK = False

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
        # --- Optional fallback path using Gemini (audio-only) ---
        if USE_GEMINI_FALLBACK and summarize_video is not None:
            with db.engine.begin() as con:
                m = con.execute(sqltext("SELECT video_url FROM meetings WHERE id=:m"), {"m": meeting_id}).first()
            if not m or not m.video_url:
                raise HTTPException(409, "No utterances found for this meeting_id. Run ingest/transcription first.")
            sv = summarize_video(
                m.video_url,
                workdir=f"./vproc/{meeting_id}",
                audio_only=True
            )
            summary_raw = {"raw_summary_text": sv.get("summary_text", "")}
            normalized = _normalize_summary(summary_raw)
            # upsert summary payload
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

            return normalized

        # --- Default: fail fast, so the UI can prompt user to ingest/transcribe first
        raise HTTPException(409, "No utterances found for this meeting_id. Run ingest/transcription first.")

    transcript = "\n".join(
        f"[{r['start_seconds']:.1f}s {r['speaker']}] {r['text']}" for r in rows
    )

    summary_raw = await summarize_meeting_json(transcript)
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

    return normalized