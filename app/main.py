# app/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.ingest import router as ingest_router
from .api.summarize import router as summarize_router
from .api.chat import router as chat_router
from .api.asr_webhook import router as asr_webhook_router


app = FastAPI(title="Meeting Storytelling API")

# CORS: adjust origins for your UI domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/api")
app.include_router(summarize_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(asr_webhook_router, prefix="/api")

