# app/rag/indexer.py
from typing import List, Dict
from ..utils.db import db
from .embedder import embed_texts
from .chunking import chunk_utterances

async def build_index(meeting_id: str):
    """
    Build vector index for a meeting's transcript.
    Fetches utterances, chunks them, embeds, and stores in chunks table.
    """
    # 1. Fetch utterances
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT speaker, start_seconds, end_seconds, text
            FROM utterances
            WHERE meeting_id = $1
            ORDER BY start_seconds
        """, meeting_id)
    
    if not rows:
        return {"message": "No utterances found"}
    
    utterances = [dict(r) for r in rows]
    
    # 2. Chunk utterances
    chunks = chunk_utterances(utterances, max_chars=900)
    
    # 3. Generate embeddings
    texts = [c["text"] for c in chunks]
    embeddings = await embed_texts(texts)
    
    # 4. Store chunks with embeddings
    async with db.acquire() as conn:
        await conn.executemany("""
            INSERT INTO chunks 
            (meeting_id, speaker, start_seconds, end_seconds, text, topic, embedding, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8)
        """, [
            (meeting_id, c["speaker"], c["start_seconds"], c["end_seconds"],
             c["text"], c.get("topic"), embeddings[i], "transcript")
            for i, c in enumerate(chunks)
        ])
    
    return {"indexed_chunks": len(chunks)}

async def index_mm_windows(meeting_id: str, windows: List[Dict], embed_model):
    """
    Index multimodal narration windows from video summarization.
    Each window becomes a chunk with topic='multimodal_narration'.
    """
    if not windows:
        return
    
    texts = [w["text"] for w in windows]
    embeddings = await embed_texts(texts)
    
    async with db.acquire() as conn:
        await conn.executemany("""
            INSERT INTO chunks
            (meeting_id, speaker, start_seconds, end_seconds, text, topic, embedding, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8)
        """, [
            (meeting_id, f"WINDOW_{w['window']}", w["start"], w["end"],
             w["text"], "multimodal_narration", embeddings[i], "multimodal")
            for i, w in enumerate(windows)
        ])