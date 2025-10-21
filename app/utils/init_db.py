from app.utils.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize database tables with correct schema"""
    
    # Test connection first
    if not supabase.test_connection():
        logger.error("❌ Cannot connect to database")
        return False
    
    logger.info("✅ Connected to database successfully")
    
    # Enable pgvector extension
    try:
        supabase.execute_query("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("✅ pgvector extension enabled")
    except Exception as e:
        logger.warning(f"⚠️  pgvector extension: {e}")
    
    # Table definitions with CORRECT schema
    table_queries = [
        # Meetings table - UUID PRIMARY KEY
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            video_url TEXT,
            status TEXT DEFAULT 'processing'
        )
        """,
        
        # ASR Jobs table
        """
        CREATE TABLE IF NOT EXISTS asr_jobs (
            job_id TEXT PRIMARY KEY,
            meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
            provider TEXT,
            status TEXT DEFAULT 'processing',
            callback_url TEXT,
            raw JSONB,
            error TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        
        # Utterances table - UUID meeting_id
        """
        CREATE TABLE IF NOT EXISTS utterances (
            id BIGSERIAL PRIMARY KEY,
            meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
            speaker TEXT,
            start_seconds DOUBLE PRECISION,
            end_seconds DOUBLE PRECISION,
            text TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        
        # Summaries table
        """
        CREATE TABLE IF NOT EXISTS summaries (
            meeting_id UUID PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,
            payload JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        
        # Chunks table - CRITICAL MISSING TABLE!
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id BIGSERIAL PRIMARY KEY,
            meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
            speaker TEXT,
            start_seconds DOUBLE PRECISION,
            end_seconds DOUBLE PRECISION,
            text TEXT,
            topic TEXT,
            source TEXT DEFAULT 'transcript',
            embedding VECTOR(1536),
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    ]
    
    # Create tables
    try:
        for i, query in enumerate(table_queries, 1):
            supabase.execute_query(query)
            logger.info(f"✅ Table {i} created successfully")
        
        # Create indexes
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_chunks_meeting ON chunks(meeting_id);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_topic ON chunks(topic);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);",
            "CREATE INDEX IF NOT EXISTS idx_utterances_meeting ON utterances(meeting_id);",
            "CREATE INDEX IF NOT EXISTS idx_asr_jobs_meeting ON asr_jobs(meeting_id);"
        ]
        
        for query in index_queries:
            supabase.execute_query(query)
        
        # Vector similarity index
        try:
            supabase.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_chunks_vector ON chunks 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """)
            logger.info("✅ Vector index created")
        except Exception as e:
            logger.warning(f"⚠️  Vector index: {e}")
        
        logger.info("🎉 All database tables initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize tables: {e}")
        return False

if __name__ == "__main__":
    initialize_database()