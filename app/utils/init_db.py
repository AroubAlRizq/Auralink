from supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize database tables"""
    
    # Test connection first
    if not supabase.test_connection():
        logger.error("❌ Cannot connect to database")
        return False
    
    logger.info("✅ Connected to database successfully")
    
    # Table definitions
    table_queries = [
        # Meetings table
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            consent BOOLEAN NOT NULL,
            status TEXT DEFAULT 'pending',
            video_url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        
        # Utterances table
        """
        CREATE TABLE IF NOT EXISTS utterances (
            id SERIAL PRIMARY KEY,
            meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            speaker TEXT NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        
        # ASR Jobs table
        """
        CREATE TABLE IF NOT EXISTS asr_jobs (
            id TEXT PRIMARY KEY,
            meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            status TEXT NOT NULL,
            callback_url TEXT,
            raw JSONB,
            error TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    ]
    
    # Create tables
    try:
        for i, query in enumerate(table_queries, 1):
            supabase.execute_query(query)
            logger.info(f"✅ Table {i} created successfully")
        
        logger.info("🎉 All database tables initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize tables: {e}")
        return False

if __name__ == "__main__":
    initialize_database()