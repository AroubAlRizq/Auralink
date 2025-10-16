# app/data/database/init.py
"""
Database initialization script.

Usage:
    python -m app.data.database.init
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.data.database.config import engine
from app.data.models import Base, create_all_tables
from sqlalchemy import text


def init_database():
    """Initialize the database with all tables and required extensions."""
    
    print("🔧 Initializing Auralink database...\n")
    
    # Enable pgvector extension
    print("1. Enabling pgvector extension...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        print("   ✓ pgvector extension enabled\n")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not enable pgvector extension: {e}\n")
        print("   You may need to run this SQL manually with superuser privileges:")
        print("   CREATE EXTENSION IF NOT EXISTS vector;\n")
    
    # Create all tables
    print("2. Creating all tables...")
    create_all_tables()
    print()
    
    # Create IVFFLAT index for vector similarity search
    print("3. Creating IVFFLAT index on chunks.embedding...")
    try:
        with engine.connect() as conn:
            # Drop index if exists
            conn.execute(text("DROP INDEX IF EXISTS chunks_embedding_ivfflat_idx;"))
            
            # Create IVFFLAT index
            # Note: lists parameter should be ~sqrt(total_rows) for optimal performance
            # We use 100 as a default; adjust based on your expected data size
            conn.execute(text(
                "CREATE INDEX chunks_embedding_ivfflat_idx ON chunks "
                "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
            ))
            conn.commit()
        print("   ✓ IVFFLAT index created successfully\n")
    except Exception as e:
        print(f"   ⚠️  Could not create IVFFLAT index: {e}")
        print("   You may need to create it manually after inserting some data:\n")
        print("   CREATE INDEX chunks_embedding_ivfflat_idx ON chunks")
        print("   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);\n")
    
    print("✅ Database initialization complete!\n")
    print("Next steps:")
    print("1. Make sure DATABASE_URL is set in your .env file")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Start using the models in your application\n")


if __name__ == "__main__":
    init_database()

