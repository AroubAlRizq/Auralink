# app/rag/indexer_service.py
import os, asyncpg
from typing import List, Dict
from app.rag.chunking import chunk_utterances, chunk_summary
from app.rag.embedder import embed_texts

DB = os.getenv("DATABASE_URL")

async def index_transcript(meeting_id: str, utterances: List[Dict]) -> int:
    """Chunk utterances -> embed -> insert into chunks with source='transcript'."""
    if not utterances:
        return 0
    chunks = chunk_utterances(utterances, max_chars=900)
    if not chunks:
        return 0
    embeds = await embed_texts([c["text"] for c in chunks])
    pool = await asyncpg.create_pool(dsn=DB, min_size=1, max_size=5)
    try:
        async with pool.acquire() as con:
            await con.executemany("""
                INSERT INTO chunks
                  (meeting_id, speaker, start_seconds, end_seconds, text, topic, source, embedding)
                VALUES ($1,$2,$3,$4,$5,$6,'transcript',$7)
            """, [
                (meeting_id, c["speaker"], c["start_seconds"], c["end_seconds"], c["text"], c.get("topic"), embeds[i])
                for i, c in enumerate(chunks)
            ])
    finally:
        await pool.close()
    return len(chunks)

async def index_summary(meeting_id: str, summary_json: Dict) -> int:
    """Chunk summary bullets -> embed -> insert into chunks with source='summary'."""
    if not summary_json:
        return 0
    chunks = chunk_summary(summary_json)
    if not chunks:
        return 0
    embeds = await embed_texts([c["text"] for c in chunks])
    pool = await asyncpg.create_pool(dsn=DB, min_size=1, max_size=5)
    try:
        async with pool.acquire() as con:
            await con.executemany("""
                INSERT INTO chunks
                  (meeting_id, speaker, start_seconds, end_seconds, text, topic, source, embedding)
                VALUES ($1,$2,$3,$4,$5,$6,'summary',$7)
            """, [
                (meeting_id, c["speaker"], c["start_seconds"], c["end_seconds"], c["text"], c.get("topic"), embeds[i])
                for i, c in enumerate(chunks)
            ])
    finally:
        await pool.close()
    return len(chunks)
