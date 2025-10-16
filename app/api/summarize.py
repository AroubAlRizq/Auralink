# app/api/summarize.py
from fastapi import APIRouter, Query, UploadFile, File, Form, HTTPException
from sqlalchemy import text as sqltext
import os, tempfile, uuid, json

from ..utils.db import DB
from ..models.inference import summarize_meeting_json  # your text-only summarizer
from ..models.video_audio_summarizer import summarize_video as mm_summarize
from ..rag.indexer import build_index  # text transcript indexer (already present)
from ..app_config import embed_model
# (Optional) multimodal narration indexer (see Step 3)
try:
    from ..rag.indexer import index_mm_windows
    HAS_MM_INDEXER = True
except Exception:
    HAS_MM_INDEXER = False

router = APIRouter(tags=["summarize"])

@router.post("/summarize")
async def summarize(
    mode: str = Query("text", pattern="^(text|multimodal)$"),
    meeting_id: str | None = Query(None),
    # For multimodal inline upload (optional)
    video_file: UploadFile | None = File(None),
    fps: int = Query(2),
    window: int = Query(30),
    max_images: int = Query(60),
    model: str | None = Query(None)
):
    """
    text mode:
      - uses transcript rows in DB -> strict JSON summary (existing behavior)
    multimodal mode:
      - uses uploaded video_file OR meeting_id->video_url stored at ingest
      - calls Gemini to create per-window narration + global summary
      - (optional) indexes narration into RAG
    """
    if mode == "text":
        if not meeting_id:
            raise HTTPException(400, "meeting_id is required for text mode.")

        # 1) Pull transcript and build a single string (or windowed prompts in your inference)
        db = DB()
        with db.engine.begin() as con:
            rows = con.execute(sqltext("""
                SELECT speaker, start_seconds, end_seconds, text
                FROM utterances
                WHERE meeting_id = :m
                ORDER BY start_seconds
            """), {"m": meeting_id}).mappings().all()
        transcript = "\n".join([f"[{r['start_seconds']:.1f}s {r['speaker']}] {r['text']}" for r in rows])

        # 2) Summarize to strict JSON
        summary_json = summarize_meeting_json(transcript)

        # 3) Upsert into summaries table to keep one source of truth
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO summaries (meeting_id, payload)
                VALUES (:m, :p::jsonb)
                ON CONFLICT (meeting_id) DO UPDATE SET payload = :p::jsonb
            """), {"m": meeting_id, "p": json.dumps(summary_json)})

        # 4) Ensure transcript is indexed for RAG (if not already)
        try:
            build_index(meeting_id)
        except Exception:
            # ignore if already indexed or indexer handles idempotency
            pass

        return summary_json

    # ---------- multimodal path ----------
    # Get a local path to the video (upload or from DB)
    if video_file:
        tmpdir = tempfile.mkdtemp(prefix="mm_")
        local_video = os.path.join(tmpdir, f"{uuid.uuid4()}_{video_file.filename}")
        with open(local_video, "wb") as f:
            f.write(await video_file.read())
    else:
        if not meeting_id:
            raise HTTPException(400, "Provide either video_file or meeting_id for multimodal mode.")
        db = DB()
        with db.engine.begin() as con:
            row = con.execute(sqltext("SELECT video_url FROM meetings WHERE id = :m"), {"m": meeting_id}).first()
        if not row or not row[0]:
            raise HTTPException(400, "No stored video_url for this meeting; upload a video_file instead.")
        local_video = row[0]  # must be accessible path or a signed URL mounted locally

    # Run Gemini video+audio summarizer
    try:
        res = mm_summarize(
            video_path=local_video,
            workdir=os.path.join(tempfile.gettempdir(), f"vproc_{uuid.uuid4().hex[:8]}"),
            fps=fps,
            window_s=window,
            max_imgs_per_chunk=max_images,
            model_name=model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        )
    except Exception as e:
        raise HTTPException(500, f"Multimodal summarization failed: {e}")

    # Optional: persist multimodal summary as part of summaries payload
    if meeting_id:
        db = DB()
        payload = {
            "executive_summary": [],  # keep empty unless you post-process to strict JSON
            "decisions": [],
            "action_items": [],
            "risks": [],
            "followups": [],
            "multimodal": {
                "narration_file": res["narration_file"],
                "summary_file": res["summary_file"],
                "windows": res["windows"]
            },
            "raw_summary_text": res["summary_text"]
        }
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO summaries (meeting_id, payload)
                VALUES (:m, :p::jsonb)
                ON CONFLICT (meeting_id) DO UPDATE SET payload = :p::jsonb
            """), {"m": meeting_id, "p": json.dumps(payload)})

        # Optional: index narration windows for RAG
        if HAS_MM_INDEXER:
            try:
                index_mm_windows(meeting_id, res["windows"], embed_model)
            except Exception:
                pass

    return res
