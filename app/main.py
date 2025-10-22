# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.aai_debug import router as aai_debug_router


# --- API Routers ---
from app.api.ingest import router as ingest_router
from app.api.ingest_file import router as ingest_file_router
from app.api.aai_poll import router as aai_poll_router
from app.api.asr_webhook import router as asr_webhook_router
from app.api.utterances import router as utterances_router
from app.api.summarize import router as summarize_router

# Optional (if you added these):
try:
    from app.api.summarize_quickdraft import router as quickdraft_router
except ImportError:
    quickdraft_router = None

try:
    from app.api.summary_status import router as summary_status_router
except ImportError:
    summary_status_router = None


# --- App initialization ---
app = FastAPI(
    title="Auralink API",
    description="Backend API for meeting transcription and summarization",
    version="1.0.0"
)

app.include_router(aai_debug_router, prefix="/api")
# --- CORS ---
# Make sure your frontend origin is allowed (adjust if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace with your frontend URL (e.g., ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers (mounted under /api) ---
app.include_router(ingest_router, prefix="/api")
app.include_router(ingest_file_router, prefix="/api")
app.include_router(aai_poll_router, prefix="/api")
app.include_router(asr_webhook_router, prefix="/api")
app.include_router(utterances_router, prefix="/api")
app.include_router(summarize_router, prefix="/api")

if quickdraft_router:
    app.include_router(quickdraft_router, prefix="/api")

if summary_status_router:
    app.include_router(summary_status_router, prefix="/api")


# --- Health Check ---
@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Root ---
@app.get("/")
def root():
    return {"message": "Auralink backend is running."}