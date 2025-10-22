# app/api/summarize_stub.py
from fastapi import APIRouter, Query

router = APIRouter(tags=["summarize"])

@router.post("/summarize")
async def summarize_stub(
    mode: str = Query("text"),
    meeting_id: str | None = Query(None),
):
    # No-op; return an empty summary shape
    return {
        "ok": True,
        "note": "summarize stub (no-op)",
        "meeting_id": meeting_id,
        "executive_summary": [],
        "decisions": [],
        "action_items": [],
        "risks": [],
        "followups": [],
    }