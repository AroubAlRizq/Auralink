# app/api/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

# RAG bits
from app.rag.embedder import embed_texts
from app.rag.retriever import search_vectors, rerank
from app.rag.composer import answer_with_citations

# General QA fallback
from app.rag.openqa import answer_open_domain, should_use_openqa

router = APIRouter(tags=["chat"])

ALLOW_GENERAL_QA = os.getenv("ALLOW_GENERAL_QA", "true").lower() in {"1", "true", "yes"}

class ChatRequest(BaseModel):
    meeting_id: str
    question: str
    top_k: int = 6

@router.post("/chat")
async def chat(req: ChatRequest):
    """
    RAG first. If recall is poor or the question is simple smalltalk, optionally fall back
    to a general LLM so the assistant can still respond helpfully.
    """
    if not req.meeting_id or not (req.question or "").strip():
        raise HTTPException(400, "meeting_id and question are required")

    question = req.question.strip()

    # --- Try RAG path
    top_score = None
    candidates = []
    try:
        q_embed = (await embed_texts([question]))[0]
        # expect each candidate optionally has a "score" (similarity). If not, we’ll keep top_score None.
        candidates = await search_vectors(req.meeting_id, q_embed, k=30)
        if candidates:
            try:
                top_score = candidates[0].get("score", None)
            except Exception:
                top_score = None
    except Exception as e:
        # Embedding/search failed; we’ll let fallback handle it if enabled
        candidates = []
        top_score = None

    use_openqa = ALLOW_GENERAL_QA and should_use_openqa(question, len(candidates), top_score)

    if use_openqa:
        # --- General small Q/A
        try:
            # optional meeting title if you store it in localStorage only; backend may not know it.
            # You could fetch from DB if you want it server-side.
            ans = await answer_open_domain(question)
        except Exception as e:
            ans = f"[general model error] {e}"
        return {"answer": ans, "sources": []}

    # --- RAG continued (rerank → compose with citations)
    try:
        top = await rerank(question, candidates, top_k=req.top_k)
        result = await answer_with_citations(question, top)
        # result shape expected: {"answer": "...", "sources": [...]}
        if not isinstance(result, dict):
            result = {"answer": str(result), "sources": []}
        return result
    except Exception as e:
        # Final safety: if RAG composition fails and fallback allowed, try general QA once.
        if ALLOW_GENERAL_QA:
            try:
                ans = await answer_open_domain(question)
                return {"answer": ans, "sources": []}
            except Exception:
                pass
        raise HTTPException(500, f"Chat failed: {e}")