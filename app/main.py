# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import all routers
from app.api.ingest import router as ingest_router
from app.api.summarize import router as summarize_router
from app.api.chat import router as chat_router
from app.api.asr_webhook import router as asr_webhook_router
# Temporarily commented out - will add back after testing
# from app.api.poll_asr import router as poll_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("🚀 Meeting Storytelling API starting up...")
    logging.info("📝 API Documentation available at /docs")
    
    # Test database connection on startup
    try:
        from app.utils.database import DatabaseManager
        db = DatabaseManager()
        if db.client.test_connection():
            logging.info("✅ Database connection successful")
        else:
            logging.error("❌ Database connection failed")
    except Exception as e:
        logging.error(f"❌ Database connection error: {e}")
    
    yield
    
    # Shutdown
    logging.info("👋 Meeting Storytelling API shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Meeting Storytelling API",
    description="AI-powered meeting transcription, summarization, and RAG chat system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(ingest_router, prefix="/api", tags=["Ingest"])
app.include_router(summarize_router, prefix="/api", tags=["Summarize"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(asr_webhook_router, prefix="/api", tags=["Webhooks"])
# app.include_router(poll_router, prefix="/api", tags=["Polling"])

# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Meeting Storytelling API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/ingest/upload",
            "ingest_url": "/api/ingest",
            "summarize": "/api/summarize",
            "chat": "/api/chat",
            "webhooks": "/api/asr/webhook/{provider}",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    from app.utils.database import DatabaseManager
    
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "components": {}
    }
    
    # Check database
    try:
        db = DatabaseManager()
        if db.client.test_connection():
            health_status["database"] = "connected"
        else:
            health_status["database"] = "disconnected"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status