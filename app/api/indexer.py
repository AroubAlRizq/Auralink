from fastapi import APIRouter
from pydantic import BaseModel
import asyncpg
import os
from rag.embedder import embed_texts
from rag.chunking import chunk_utterances, chunk_summary

router = APIRouter()
DB = os.getenv("DATABASE_URL")

class IndexRequest(BaseModel):
    meeting_id: str
    source: str = "transcript"   # or "summary"
    items: list  # utterances or summary objects as defined above

@router.post("/index")
async def index_chunks(req: IndexRequest):
    pool = await asyncpg.create_pool(dsn=DB, min_size=1, max_size=5)

    if req.source == "transcript":
        chunks = chunk_utterances(req.items, max_chars=900)
    else:
        # req.items expected to be a single dict summary
        chunks = chunk_summary(req.items)

    embeds = await embed_texts([c["text"] for c in chunks])

    async with pool.acquire() as con:
        await con.executemany("""
            INSERT INTO chunks (meeting_id, speaker, start_seconds, end_seconds, text, topic, embedding, source)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        """, [
            (req.meeting_id, c["speaker"], c["start_seconds"], c["end_seconds"], c["text"], c.get("topic"),
             embeds[i], req.source)
            for i, c in enumerate(chunks)
        ])
    await pool.close()
    return {"inserted": len(chunks)}

