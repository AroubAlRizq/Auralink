# app/api/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from ..rag.embedder import embed_texts
from ..rag.retriever import search_vectors, rerank
from ..rag.composer import answer_with_citations

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    meeting_id: str
    question: str
    top_k: int = 6

@router.post("/chat")
async def chat(req: ChatRequest):
    """
    RAG-powered chat endpoint.
    1. Embed question
    2. Vector search chunks
    3. Rerank results
    4. Generate answer with LLM
    """
    # 1. Embed the question
    q_embed = (await embed_texts([req.question]))[0]
    
    # 2. Vector search (retrieves top 30 candidates)
    candidates = await search_vectors(req.meeting_id, q_embed, k=30)
    
    # 3. Rerank to get best top_k
    top = await rerank(req.question, candidates, top_k=req.top_k)
    
    # 4. Generate answer with citations
    result = await answer_with_citations(req.question, top)
    
    return result