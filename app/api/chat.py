# app/api/chat.py
from fastapi import APIRouter
from pydantic import BaseModel

# ❌ BEFORE: from rag.embedder / rag.retriever / rag.composer
# ✅ AFTER:
from app.rag.embedder import embed_texts
from app.rag.retriever import search_vectors, rerank
from app.rag.composer import answer_with_citations

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    meeting_id: str
    question: str
    top_k: int = 6

@router.post("/chat")
async def chat(req: ChatRequest):
    q_embed = (await embed_texts([req.question]))[0]
    candidates = await search_vectors(req.meeting_id, q_embed, k=30)
    top = await rerank(req.question, candidates, top_k=req.top_k)
    result = await answer_with_citations(req.question, top)
    return result