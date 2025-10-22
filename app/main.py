# app/main.py
from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text as sqltext

# Routers
from app.api.ingest import router as ingest_router
from app.api.ingest_file import router as ingest_file_router
from app.api.aai_poll import router as aai_poll_router
from app.api.asr_webhook import router as asr_webhook_router
from app.api.utterances import router as utterances_router
from app.api.summarize import router as summarize_router
from app.api.chat import router as chat_router  # RAG chat

# Optional routers (best-effort)
try:
    from app.api.summarize_quickdraft import router as quickdraft_router
except Exception:
    quickdraft_router = None
try:
    from app.api.summary_status import router as summary_status_router
except Exception:
    summary_status_router = None

# DB helpers
from app.utils.db import DB, dispose_engine


# ---------- App ----------
app = FastAPI(
    title="Auralink API",
    description="Backend API for meeting transcription, summarization, and RAG chat.",
    version="2.0.0",
)

# ---------- CORS ----------
# For dev you can allow all; in prod, set PUBLIC_FRONTEND_ORIGIN
_frontend_origins = os.getenv("PUBLIC_FRONTEND_ORIGIN", "*").strip()
allow_origins = ["*"] if _frontend_origins == "*" or not _frontend_origins else [
    o.strip() for o in _frontend_origins.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
app.include_router(ingest_router, prefix="/api")
app.include_router(ingest_file_router, prefix="/api")
app.include_router(aai_poll_router, prefix="/api")
app.include_router(asr_webhook_router, prefix="/api")
app.include_router(utterances_router, prefix="/api")
app.include_router(summarize_router, prefix="/api")
app.include_router(chat_router, prefix="/api")  # RAG Chat

if quickdraft_router:
    app.include_router(quickdraft_router, prefix="/api")
if summary_status_router:
    app.include_router(summary_status_router, prefix="/api")


# ---------- Lifecycle (init + clean DB connections) ----------
@app.on_event("startup")
async def startup_event():
    # Warm up a single lightweight DB round-trip and immediately release it.
    db = DB()
    with db.engine.connect() as conn:
        conn.execute(sqltext("SELECT 1"))
    print("✅ Database connectivity OK")

@app.on_event("shutdown")
async def shutdown_event():
    # Dispose engine to avoid leaking connections on reload/exit
    dispose_engine()
    print("🧹 Disposed DB engine")


# ---------- Health / Root ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Auralink backend is running with RAG + ASR + Chat."}