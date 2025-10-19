# app/api/summarize.py
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from sqlalchemy import text as sqltext
import os, tempfile, uuid, json

from app.utils.db import DB
from app.rag.composer import summarize_meeting_json            # you added this async fn
from app.models.video_audio_summarizer import summarize_video as mm_summarize

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
    model: str | None = Query(None),
):
    """
    text mode:
      - reads utterances for meeting_id
      - builds transcript string
      - calls summarize_meeting_json (LLM) -> strict JSON
      - upserts into summaries(meeting_id, payload)

    multimodal mode:
      - uses uploaded file OR meetings.video_url
      - runs Gemini-based video+audio summarizer
      - saves result under summaries(meeting_id, payload.multimodal)
    """
    db = DB()

    if mode == "text":
        if not meeting_id:
            raise HTTPException(400, "meeting_id is required for text mode.")

        # 1) Pull transcript
        with db.engine.begin() as con:
            rows = con.execute(sqltext("""
                SELECT speaker, start_seconds, end_seconds, text
                FROM utterances
                WHERE meeting_id = :m
                ORDER BY start_seconds
            """), {"m": meeting_id}).mappings().all()

        if not rows:
            raise HTTPException(404, "No utterances found for this meeting. Run ingest/ASR first.")

        transcript = "\n".join(
            f"[{r['start_seconds']:.1f}s {r['speaker']}] {r['text']}".strip()
            for r in rows if r["text"]
        )

        # 2) Summarize (async)
        summary_json = await summarize_meeting_json(transcript)

        # 3) Upsert into summaries
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO summaries (meeting_id, payload)
                VALUES (:m, :p::jsonb)
                ON CONFLICT (meeting_id) DO UPDATE SET payload = :p::jsonb
            """), {"m": meeting_id, "p": json.dumps(summary_json)})

        return summary_json

    # ---------- multimodal path ----------
    # Resolve local video path: upload OR fetch from DB
    if video_file:
        tmpdir = tempfile.mkdtemp(prefix="mm_")
        local_video = os.path.join(tmpdir, f"{uuid.uuid4()}_{video_file.filename}")
        with open(local_video, "wb") as f:
            f.write(await video_file.read())
    else:
        if not meeting_id:
            raise HTTPException(400, "Provide either video_file or meeting_id for multimodal mode.")
        with db.engine.begin() as con:
            row = con.execute(sqltext("SELECT video_url FROM meetings WHERE id = :m"),
                              {"m": meeting_id}).first()
        if not row or not row[0]:
            raise HTTPException(400, "No stored video_url for this meeting; upload a video_file instead.")
        local_video = row[0]  # must be accessible path or mapped URL

    # Run Gemini video+audio summarizer
    try:
        res = mm_summarize(
            video_path=local_video,
            workdir=os.path.join(tempfile.gettempdir(), f"vproc_{uuid.uuid4().hex[:8]}"),
            fps=fps,
            window_s=window,
            max_imgs_per_chunk=max_images,
            model_name=model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
    except Exception as e:
        raise HTTPException(500, f"Multimodal summarization failed: {e}")

    # Persist multimodal payload (if meeting_id supplied)
    if meeting_id:
        payload = {
            "executive_summary": [],
            "decisions": [],
            "action_items": [],
            "risks": [],
            "followups": [],
            "multimodal": {
                "narration_file": res["narration_file"],
                "summary_file": res["summary_file"],
                "windows": res["windows"],
            },
            "raw_summary_text": res["summary_text"],
        }
        with db.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO summaries (meeting_id, payload)
                VALUES (:m, :p::jsonb)
                ON CONFLICT (meeting_id) DO UPDATE SET payload = :p::jsonb
            """), {"m": meeting_id, "p": json.dumps(payload)})

    return res
