from fastapi import APIRouter
from pydantic import BaseModel
import os, httpx
from rag.embedder import embed_texts
from rag.retriever import search_vectors, rerank
from rag.composer import answer_with_citations

router = APIRouter()

class ChatRequest(BaseModel):
    meeting_id: str
    question: str
    top_k: int = 6

@router.post("/chat")
async def chat(req: ChatRequest):
    # 1) embed question
    q_embed = (await embed_texts([req.question]))[0]
    # 2) vector search
    candidates = await search_vectors(req.meeting_id, q_embed, k=30)
    # 3) rerank
    top = await rerank(req.question, candidates, top_k=req.top_k)
    # 4) LLM compose
    result = await answer_with_citations(req.question, top)
    return result

