# app/api/summarize.py
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
import os, tempfile, uuid, json
import asyncio
import random
from app.rag.composer import summarize_meeting_json
from app.models.video_audio_summarizer import summarize_video as mm_summarize
from app.utils.database import DatabaseManager

# ✅ auto-index service (for summary bullets; transcript is auto-indexed in webhook)
from app.rag.indexer_service import index_summary

# Optional multimodal window indexer if you implemented it
try:
    from app.rag.indexer import index_mm_windows
    HAS_MM_INDEXER = True
except Exception:
    HAS_MM_INDEXER = False

router = APIRouter(tags=["summarize"])

@router.post("/summarize")
async def summarize(
    mode: str = Query("text", pattern="^(text|multimodal)$"),
    meeting_id: str | None = Query(None),
    video_file: UploadFile | None = File(None),
    fps: int = Query(2),
    window: int = Query(30),
    max_images: int = Query(60),
    model: str | None = Query(None)
):
    if mode == "text":
        if not meeting_id:
            raise HTTPException(400, "meeting_id is required for text mode.")

        db = DatabaseManager()
        
        # Build transcript from utterances using DatabaseManager method
        query = """
            SELECT speaker, start_seconds, end_seconds, text
            FROM utterances
            WHERE meeting_id = %s
            ORDER BY start_seconds
        """
        rows = db.client.execute_query(query, (meeting_id,))

        transcript = "\n".join([f"[{row[1]:.1f}s {row[0]}] {row[3]}" for row in rows])

        # Summarize → strict JSON
        summary_json = await summarize_meeting_json(transcript)
        summary_json["meeting_id"] = meeting_id

        # Upsert into summaries using the existing method
        db.upsert_summary(meeting_id, summary_json)

        # ✅ Auto-index summary bullets for RAG
        try:
            await index_summary(meeting_id, summary_json)
        except Exception:
            # don't fail the API if indexing fails
            pass

        return summary_json

    # -------- multimodal path --------
    # get local path
    if video_file:
        tmpdir = tempfile.mkdtemp(prefix="mm_")
        local_video = os.path.join(tmpdir, f"{uuid.uuid4()}_{video_file.filename}")
        with open(local_video, "wb") as f:
            f.write(await video_file.read())
    else:
        if not meeting_id:
            raise HTTPException(400, "Provide either video_file or meeting_id for multimodal mode.")
        
        db = DatabaseManager()
        query = "SELECT video_url FROM meetings WHERE id = %s"
        result = db.client.execute_query(query, (meeting_id,))
        
        if not result or not result[0] or not result[0][0]:
            raise HTTPException(400, "No stored video_url for this meeting; upload a video_file instead.")
        local_video = result[0][0]

    # run Gemini
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

    # persist multimodal summary in summaries payload
    if meeting_id:
        db = DatabaseManager()
        payload = {
            "meeting_id": meeting_id,
            "executive_summary": [],
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
        
        # Use the existing upsert_summary method
        db.upsert_summary(meeting_id, payload)

        # (optional) index multimodal windows if you have a helper
        if HAS_MM_INDEXER:
            try:
                index_mm_windows(meeting_id, res["windows"])
            except Exception:
                pass

    return res