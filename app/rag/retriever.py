import os, asyncpg, httpx
from typing import List, Dict

DB = os.getenv("DATABASE_URL")
RERANK_PROVIDER = os.getenv("RERANK_PROVIDER","cohere")
RERANK_MODEL = os.getenv("RERANK_MODEL","rerank-3.5")
RERANK_API_KEY = os.getenv("RERANK_API_KEY")

async def search_vectors(meeting_id: str, query_embed: List[float], k: int = 30) -> List[Dict]:
    pool = await asyncpg.create_pool(dsn=DB)
    async with pool.acquire() as con:
        rows = await con.fetch("""
            SELECT id, speaker, start_seconds, end_seconds, text, topic
            FROM chunks
            WHERE meeting_id = $1
            ORDER BY embedding <-> $2
            LIMIT $3
        """, meeting_id, query_embed, k)
    await pool.close()
    return [dict(r) for r in rows]

async def rerank(query: str, candidates: List[Dict], top_k: int = 6) -> List[Dict]:
    if not candidates: return []
    if RERANK_PROVIDER == "cohere":
        url = "https://api.cohere.ai/v1/rerank"
        headers = {"Authorization": f"Bearer {RERANK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": RERANK_MODEL, "query": query, "documents": [c["text"] for c in candidates], "top_n": top_k}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            ranks = resp.json()["results"]
        # map back
        picked = [candidates[r["index"]] for r in ranks]
        return picked[:top_k]
    return candidates[:top_k]

