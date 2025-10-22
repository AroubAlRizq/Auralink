# app/utils/db.py
from __future__ import annotations
import os
from typing import Iterable, List, Dict, Any, Optional

from sqlalchemy import create_engine, text as sqltext
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

# Single, lazily-created engine shared across the app.
# Using NullPool avoids keeping idle connections open to Supabase PgBouncer.
_ENGINE: Optional[Engine] = None


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(
            _database_url(),
            # IMPORTANT for Supabase / PgBouncer "session" mode in dev:
            poolclass=NullPool,        # open/close per .begin() call; prevents pool exhaustion
            pool_pre_ping=True,        # validates stale conns
            future=True,
        )
    return _ENGINE


def dispose_engine() -> None:
    """Dispose the current engine (used on app shutdown / reload)."""
    global _ENGINE
    if _ENGINE is not None:
        try:
            _ENGINE.dispose()
        finally:
            _ENGINE = None


class DB:
    """
    Thin helper so existing code can do: DB().engine.begin()
    and also use a few convenience write helpers.
    """
    def __init__(self) -> None:
        self.engine = get_engine()

    # ----- Convenience helpers used elsewhere -----

    def bulk_insert_utterances(self, meeting_id: str, items: Iterable[Dict[str, Any]]) -> int:
        if not items:
            return 0
        count = 0
        with self.engine.begin() as con:
            for u in items:
                con.execute(sqltext("""
                    INSERT INTO utterances (meeting_id, speaker, start_seconds, end_seconds, text)
                    VALUES (:m, :spk, :ss, :es, :txt)
                """), {
                    "m": meeting_id,
                    "spk": u.get("speaker") or u.get("speaker_label") or "Speaker",
                    "ss": float(u.get("start_seconds", 0.0)),
                    "es": float(u.get("end_seconds", 0.0)),
                    "txt": (u.get("text") or "").strip(),
                })
                count += 1
        return count

    def update_meeting_status(self, meeting_id: str, status: str) -> None:
        with self.engine.begin() as con:
            con.execute(sqltext("""
                UPDATE meetings SET status=:s WHERE id=:m
            """), {"s": status, "m": meeting_id})

    def update_asr_job(self, job_id: str, *, status: str, raw: Any | None = None, error: str | None = None) -> None:
        with self.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO asr_jobs (job_id, status, error, raw)
                VALUES (:id, :st, :err, CAST(:raw AS jsonb))
                ON CONFLICT (job_id) DO UPDATE
                    SET status=EXCLUDED.status,
                        error=EXCLUDED.error,
                        raw=EXCLUDED.raw
            """), {"id": job_id, "st": status, "err": error, "raw": None if raw is None else str(raw)})

    def upsert_asr_job(self, *, job_id: str, meeting_id: str, provider: str, status: str, callback_url: str | None) -> None:
        with self.engine.begin() as con:
            con.execute(sqltext("""
                INSERT INTO asr_jobs (job_id, meeting_id, provider, status, callback_url)
                VALUES (:id, :m, :p, :s, :cb)
                ON CONFLICT (job_id) DO UPDATE
                    SET meeting_id=EXCLUDED.meeting_id,
                        provider=EXCLUDED.provider,
                        status=EXCLUDED.status,
                        callback_url=EXCLUDED.callback_url
            """), {"id": job_id, "m": meeting_id, "p": provider, "s": status, "cb": callback_url})

    def meeting_id_from_job(self, job_id: str) -> str | None:
        with self.engine.begin() as con:
            row = con.execute(sqltext("""
                SELECT meeting_id FROM asr_jobs WHERE job_id=:id
            """), {"id": job_id}).first()
        return row[0] if row else None