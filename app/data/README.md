# Auralink Database Models

SQLAlchemy ORM models for Supabase PostgreSQL database with pgvector support.

## Structure

```
app/data/
├── database/
│   ├── __init__.py          # Exports database config
│   ├── config.py            # Database engine & session configuration
│   └── init.py              # Database initialization script
├── models/
│   ├── __init__.py          # Exports all models
│   ├── base.py              # Base imports (re-exports from database)
│   ├── meeting.py           # Meeting model
│   ├── utterance.py         # Utterance model (ASR transcripts)
│   ├── summary.py           # Summary model (JSONB)
│   ├── chunk.py             # Chunk model (with embeddings)
│   ├── asr_job.py           # ASR job tracking
│   └── file.py              # File metadata
├── examples.py              # Usage examples
└── README.md                # This file
```

## Setup

### 1. Environment Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://user:password@host:port/database
GOOGLE_API_KEY=your_google_api_key
```

For Supabase, your `DATABASE_URL` format is:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `sqlalchemy` - ORM framework
- `psycopg2-binary` - PostgreSQL adapter
- `pgvector` - Vector extension support

### 3. Initialize Database

Run the initialization script to create all tables and indexes:

```bash
python -m app.data.database.init
```

This will:
1. Enable the `pgvector` extension
2. Create all tables
3. Create the IVFFLAT index for vector similarity search

## Models Overview

### Meeting
Stores metadata about uploaded meetings/videos.
- **Primary Key**: `id` (UUID)
- **Status values**: uploaded, asr_started, asr_done, indexed, summarized, error
- **Relationships**: utterances, summary, chunks, asr_jobs, files

### Utterance
Individual speech segments from ASR transcription.
- **Primary Key**: `id` (BigInt, auto-increment)
- **Foreign Key**: `meeting_id` → meetings.id
- **Indexes**: meeting_id, (meeting_id, start_seconds)

### Summary
Structured meeting minutes stored as JSONB.
- **Primary Key**: `meeting_id` (1-to-1 with Meeting)
- **Payload**: JSONB containing executive summary, key events, action items, etc.

### Chunk
Text chunks with embeddings for RAG/semantic search.
- **Primary Key**: `id` (BigInt, auto-increment)
- **Foreign Key**: `meeting_id` → meetings.id
- **Vector Field**: `embedding` (3072 dimensions for text-embedding-3-large)
- **Indexes**: meeting_id, (meeting_id, start_seconds), IVFFLAT on embedding

### AsrJob
Tracks automatic speech recognition job status.
- **Primary Key**: `id` (provider job ID)
- **Foreign Key**: `meeting_id` → meetings.id
- **Providers**: assemblyai, deepgram, whisper, etc.

### File
Metadata for uploaded/generated files.
- **Primary Key**: `id` (BigInt, auto-increment)
- **Foreign Key**: `meeting_id` → meetings.id
- **Kinds**: upload, narration, summary, other

## Usage

### Basic Operations

```python
from app.data.models import SessionLocal, Meeting, Utterance, Summary

# Create a session
db = SessionLocal()

try:
    # Create a meeting
    meeting = Meeting(
        title="Team Standup",
        video_url="https://example.com/video.mp4",
        consent=True,
        status="uploaded"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    # Add utterances
    utterance = Utterance(
        meeting_id=meeting.id,
        speaker="SPEAKER_0",
        start_seconds=0.0,
        end_seconds=5.2,
        text="Hello everyone!"
    )
    db.add(utterance)
    db.commit()
    
    # Query with relationships
    meeting = db.query(Meeting).first()
    print(f"Meeting: {meeting.title}")
    print(f"Utterances: {len(meeting.utterances)}")
    
finally:
    db.close()
```

### Using with FastAPI

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.data.models import get_db, Meeting

app = FastAPI()

@app.get("/meetings")
def list_meetings(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).all()
    return meetings

@app.post("/meetings")
def create_meeting(title: str, video_url: str, db: Session = Depends(get_db)):
    meeting = Meeting(title=title, video_url=video_url, consent=True)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting
```

### Vector Similarity Search

```python
from app.data.models import SessionLocal, Chunk

db = SessionLocal()

# Get embedding from OpenAI (example)
query_embedding = [0.1, 0.2, ...]  # 3072-dimensional vector

# Find similar chunks
results = db.query(
    Chunk,
    Chunk.embedding.cosine_distance(query_embedding).label("distance")
).order_by("distance").limit(5).all()

for chunk, distance in results:
    print(f"Distance: {distance:.4f} - {chunk.text[:50]}...")
```

## Vector Index Configuration

The IVFFLAT index is optimized for fast approximate nearest neighbor search:

```sql
CREATE INDEX chunks_embedding_ivfflat_idx ON chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Performance Tips**:
- `lists` parameter should be approximately `sqrt(total_rows)`
- For 10,000 chunks, use `lists = 100`
- For 100,000 chunks, use `lists = 316`
- For 1,000,000 chunks, use `lists = 1000`

## Migration from Raw SQL

If you have existing tables created via `schemas/db.sql`, you can:

1. **Option A**: Drop and recreate (⚠️ loses data)
   ```python
   from app.data.models import Base, engine
   Base.metadata.drop_all(engine)
   Base.metadata.create_all(engine)
   ```

2. **Option B**: Use Alembic for migrations (recommended for production)
   ```bash
   pip install alembic
   alembic init alembic
   # Configure alembic.ini and env.py
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

## Testing

See `examples.py` for comprehensive usage examples:

```bash
python -m app.data.examples
```

## Troubleshooting

### pgvector Extension Not Found
If you get an error about the `vector` extension:
1. Connect to your Supabase database
2. Run: `CREATE EXTENSION IF NOT EXISTS vector;`

### IVFFLAT Index Creation Fails
The IVFFLAT index requires data in the table. Insert some chunks first, then create the index manually.

### Connection Issues
Verify your `DATABASE_URL` is correct:
```python
from app.data.models import engine
with engine.connect() as conn:
    print("✓ Connected successfully!")
```

## Additional Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Supabase Database Guide](https://supabase.com/docs/guides/database)

