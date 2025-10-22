# app/rag/retriever.py
from __future__ import annotations

from typing import Any, Dict, List, Sequence
from sqlalchemy import text as sqltext
from sqlalchemy.exc import ProgrammingError, OperationalError

from app.utils.db import DB

# You can override the index table name by env var if you like.
# Table is expected to have: meeting_id TEXT, text TEXT, speaker TEXT,
# start_seconds FLOAT, end_seconds FLOAT, embedding VECTOR   (pgvector)
import os
INDEX_TABLE = os.getenv("RAG_INDEX_TABLE", "rag_chunks")


def _fmt_vec(v: Sequence[float], precision: int = 6) -> str:
    """Format a Python vector as a pgvector-compatible string."""
    parts = []
    for x in v:
        try:
            xf = float(x)
        except Exception:
            xf = 0.0
        parts.append(f"{xf:.{precision}f}")
    return "[" + ",".join(parts) + "]"


def _rows_to_dicts(rows) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        # keep a consistent shape expected by composer/chat
        d.setdefault("speaker", None)
        d.setdefault("start_seconds", None)
        d.setdefault("end_seconds", None)
        d.setdefault("text", "")
        if "score" not in d:
            d["score"] = None
        out.append(d)
    return out


async def search_vectors(meeting_id: str, query_vec: Any, k: int = 30) -> List[Dict[str, Any]]:
    """
    Vector search primary; LIKE fallback if pgvector or table is missing.
    - meeting_id: scope
    - query_vec: list[float] or string "[...]" accepted
    - k: number of candidates to return (pre-rerank)
    """
    db = DB()

    # Normalize vector to a string for pgvector CAST
    if isinstance(query_vec, (list, tuple)):
        qvec = _fmt_vec(query_vec)
    else:
        qvec = str(query_vec)

    # 1) Try pgvector over INDEX_TABLE
    try:
        with db.engine.begin() as con:
            rows = con.execute(
                sqltext(f"""
                    SELECT
                        speaker,
                        start_seconds,
                        end_seconds,
                        text,
                        (embedding <-> CAST(:vec AS vector)) AS score
                    FROM {INDEX_TABLE}
                    WHERE meeting_id = :m
                    ORDER BY score ASC
                    LIMIT :k
                """),
                {"vec": qvec, "m": meeting_id, "k": max(1, int(k))}
            ).mappings().all()
        if rows:
            return _rows_to_dicts(rows)
    except (ProgrammingError, OperationalError):
        # Missing table/extension or wrong schema -> fall back
        pass
    except Exception:
        # Any other issue -> fall back
        pass

    # 2) Fallback: simple LIKE search over utterances
    try:
        needle = "%"  # default
        # use a couple of keywords from the user's question if it looks like a vec string
        if qvec.startswith("[") and qvec.endswith("]"):
            # no text; just show recent utterances
            with db.engine.begin() as con:
                rows = con.execute(
                    sqltext("""
                        SELECT speaker, start_seconds, end_seconds, text
                        FROM utterances
                        WHERE meeting_id=:m
                        ORDER BY start_seconds ASC
                        LIMIT :k
                    """),
                    {"m": meeting_id, "k": max(10, int(k))}
                ).mappings().all()
            return _rows_to_dicts(rows)

        # Otherwise, qvec may be plain text (rare here), try LIKE
        needle = f"%{qvec[:64]}%"
        with db.engine.begin() as con:
            rows = con.execute(
                sqltext("""
                    SELECT speaker, start_seconds, end_seconds, text
                    FROM utterances
                    WHERE meeting_id=:m AND (text ILIKE :q OR speaker ILIKE :q)
                    ORDER BY start_seconds ASC
                    LIMIT :k
                """),
                {"m": meeting_id, "q": needle, "k": max(10, int(k))}
            ).mappings().all()
        if rows:
            return _rows_to_dicts(rows)
    except Exception:
        pass

    # 3) Last resort: latest utterances
    with db.engine.begin() as con:
        rows = con.execute(
            sqltext("""
                SELECT speaker, start_seconds, end_seconds, text
                FROM utterances
                WHERE meeting_id=:m
                ORDER BY start_seconds DESC
                LIMIT :k
            """),
            {"m": meeting_id, "k": max(10, int(k))}
        ).mappings().all()
    rows = list(reversed(rows))
    return _rows_to_dicts(rows)


async def rerank(question: str, candidates: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    """
    Lightweight reranker:
    - If COHERE_* env is configured and you have a proper reranker client, call it here.
    - Otherwise do a simple signal: longer snippets & early timestamps get a tiny boost.
    """
    if not candidates:
        return []

    # If you have a real reranker, plug it here and return early.
    # Example:
    # return await real_rerank(question, candidates, top_k=top_k)

    def score(c: Dict[str, Any]) -> float:
        txt = (c.get("text") or "").strip()
        length_bonus = min(len(txt), 600) / 600.0       # 0..1
        start = c.get("start_seconds")
        recency_bonus = 0.0
        if isinstance(start, (int, float)):
            # mild preference for later parts of meeting
            recency_bonus = min(max(start, 0.0) / 3600.0, 1.0) * 0.2  # up to +0.2
        base = 1.0 - float(c.get("score") or 0.0) if c.get("score") is not None else 0.5
        return base + 0.3 * length_bonus + recency_bonus

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[: max(1, int(top_k))]