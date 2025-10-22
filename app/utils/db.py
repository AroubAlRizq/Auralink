# app/utils/db.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

class DB:
    def __init__(self):
        self.engine = engine

    # --- meetings
    def set_meeting_video_url(self, meeting_id: str, video_url: str):
        with self.engine.begin() as con:
            con.execute(text("update meetings set video_url=:u where id=:id"),
                        {"u": video_url, "id": meeting_id})

    def update_meeting_status(self, meeting_id: str, status: str):
        with self.engine.begin() as con:
            con.execute(text("update meetings set status=:s where id=:id"),
                        {"s": status, "id": meeting_id})

    # --- utterances
    def bulk_insert_utterances(self, meeting_id: str, utts: list[dict]):
        if not utts: return
        values_sql = ",".join([f"(:m, :sp{i}, :st{i}, :en{i}, :tx{i})" for i in range(len(utts))])
        params = {"m": meeting_id}
        for i, u in enumerate(utts):
            params[f"sp{i}"] = u["speaker"]
            params[f"st{i}"] = float(u["start_seconds"])
            params[f"en{i}"] = float(u["end_seconds"])
            params[f"tx{i}"] = u["text"]
        with self.engine.begin() as con:
            con.execute(text(f"""
                insert into utterances (meeting_id, speaker, start_seconds, end_seconds, text)
                values {values_sql}
            """), params)

    # --- asr_jobs: NOTE the column is job_id (not id)
    def upsert_asr_job(self, job_id: str, meeting_id: str, provider: str, status: str,
                       callback_url: str | None = None, raw=None, error: str | None = None):
        with self.engine.begin() as con:
            con.execute(text("""
                insert into asr_jobs (job_id, meeting_id, provider, status, callback_url, raw, error)
                values (:id, :m, :p, :s, :cb, to_jsonb(:raw::text), :err)
                on conflict (job_id) do update set
                  meeting_id=excluded.meeting_id,
                  provider=excluded.provider,
                  status=excluded.status,
                  callback_url=excluded.callback_url,
                  raw=excluded.raw,
                  error=excluded.error
            """), {"id": job_id, "m": meeting_id, "p": provider, "s": status,
                   "cb": callback_url, "raw": str(raw) if raw is not None else None, "err": error})

    def update_asr_job(self, job_id: str, status: str, raw=None, error: str | None = None):
        with self.engine.begin() as con:
            con.execute(text("""
                update asr_jobs
                set status=:s,
                    raw = coalesce(raw, to_jsonb(:raw::text)),
                    error = coalesce(:err, error)
                where job_id=:id
            """), {"id": job_id, "s": status, "raw": str(raw) if raw is not None else None, "err": error})