# app/api/index_stub.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["index"])

class IndexReq(BaseModel):
    meeting_id: str

@router.post("/index")
async def index_stub(req: IndexReq):
    # No-op; just acknowledge so the UI doesn’t error
    return {"ok": True, "note": "index stub (no-op)", "meeting_id": req.meeting_id}