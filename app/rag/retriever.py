import os, httpx
from typing import List, Dict
from app.utils.database import DatabaseManager

RERANK_PROVIDER = os.getenv("RERANK_PROVIDER", "cohere")
RERANK_MODEL = os.getenv("RERANK_MODEL", "rerank-3.5")
RERANK_API_KEY = os.getenv("RERANK_API_KEY")

async def search_vectors(meeting_id: str, query_embed: List[float], k: int = 30) -> List[Dict]:
    """Search for similar chunks using vector similarity"""
    db = DatabaseManager()
    
    # Convert embedding list to PostgreSQL array format
    embed_str = "[" + ",".join(map(str, query_embed)) + "]"
    
    query = """
        SELECT id, speaker, start_seconds, end_seconds, text, topic
        FROM chunks
        WHERE meeting_id = %s
        ORDER BY embedding <-> %s::vector
        LIMIT %s
    """
    
    result = db.client.execute_query(query, (meeting_id, embed_str, k))
    
    # Convert rows to dictionaries
    candidates = []
    for row in result:
        candidates.append({
            "id": row[0],
            "speaker": row[1],
            "start_seconds": row[2],
            "end_seconds": row[3],
            "text": row[4],
            "topic": row[5]
        })
    
    return candidates

async def rerank(query: str, candidates: List[Dict], top_k: int = 6) -> List[Dict]:
    """Rerank candidates using Cohere rerank API"""
    if not candidates:
        return []
    
    if RERANK_PROVIDER == "cohere":
        if not RERANK_API_KEY:
            # If no rerank API key, just return top_k candidates
            return candidates[:top_k]
            
        url = "https://api.cohere.ai/v1/rerank"
        headers = {
            "Authorization": f"Bearer {RERANK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": RERANK_MODEL,
            "query": query,
            "documents": [c["text"] for c in candidates],
            "top_n": top_k
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                ranks = resp.json()["results"]
            
            # Map back to original candidates
            picked = [candidates[r["index"]] for r in ranks]
            return picked[:top_k]
        except Exception as e:
            print(f"Rerank failed: {e}, falling back to top_k")
            return candidates[:top_k]
    
    return candidates[:top_k]