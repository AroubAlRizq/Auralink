# Supabase Integration Structure

This document outlines the complete structure of the Supabase integration for Auralink.

## Folder Structure

```
app/supabase/
├── __init__.py                      # Main module exports
├── README.md                        # Complete documentation
├── STRUCTURE.md                     # This file
├── client.py                        # Supabase client initialization
├── example_usage.py                 # Usage examples and demos
│
├── services/                        # Service layer for database operations
│   ├── __init__.py                  # Service exports
│   ├── base_service.py              # Base service with common CRUD operations
│   ├── meeting_service.py           # Meeting model service
│   ├── file_service.py              # File model service
│   ├── chunk_service.py             # Chunk model service (with vector search)
│   ├── summary_service.py           # Summary model service
│   ├── utterance_service.py         # Utterance model service
│   └── asr_job_service.py           # ASR Job model service
│
└── sql/                             # SQL setup and migration scripts
    ├── setup.sql                    # Complete database setup script
    └── match_chunks.sql             # Vector similarity search functions
```

## Component Overview

### Core Components

#### `client.py`
- **Purpose**: Initialize and manage Supabase client connections
- **Key Functions**:
  - `get_supabase_client()` - Get client with anon key (user-level)
  - `get_admin_client()` - Get client with service role key (admin-level)
  - `get_client(use_admin)` - Get cached client instance

#### `services/base_service.py`
- **Purpose**: Base class providing common database operations
- **Key Methods**:
  - `create(data)` - Create single record
  - `create_many(data)` - Batch create records
  - `get_by_id(id)` - Get record by ID
  - `get_all()` - Get all records
  - `update(id, data)` - Update record
  - `delete(id)` - Delete record
  - `filter(filters)` - Filter records
  - `order_by(column)` - Get ordered records
  - `count(filters)` - Count records

### Model Services

#### `meeting_service.py` - Meeting Operations
- Create, read, update, delete meetings
- Query by status
- Get recent meetings
- Get meeting with all relations (files, utterances, chunks, etc.)

#### `file_service.py` - File Operations
- Create file metadata
- Query files by meeting
- Filter by file type (upload, narration, summary, other)
- Update public URLs

#### `chunk_service.py` - Chunk Operations (RAG/Vector Search)
- Create text chunks with embeddings
- Batch operations for efficiency
- Query by meeting, time range, topic
- **Semantic search** using vector similarity
- Update embeddings

#### `summary_service.py` - Summary Operations
- Create/update meeting summaries
- Upsert operations (create or update)
- Query summary fields from JSONB payload
- Store structured meeting minutes

#### `utterance_service.py` - Utterance Operations (Transcripts)
- Create ASR transcription segments
- Batch create utterances
- Query by speaker, time range
- Generate full formatted transcripts
- Text search in utterances

#### `asr_job_service.py` - ASR Job Tracking
- Track ASR processing jobs
- Update job status
- Query by provider, status
- Store raw provider payloads
- Error handling and logging

### SQL Scripts

#### `sql/setup.sql`
- Complete database schema
- Table creation with constraints
- Index creation for performance
- Triggers for auto-updating timestamps
- Vector similarity search functions
- Optional RLS policies

#### `sql/match_chunks.sql`
- Vector similarity search function
- IVFFlat index for fast vector search
- Cosine similarity ranking
- Per-meeting and global search functions

## Data Flow

```
1. Meeting Creation
   └─> meeting_service.create_meeting()
       └─> Supabase: INSERT INTO meetings

2. File Upload
   └─> file_service.create_file()
       └─> Supabase: INSERT INTO files

3. ASR Processing
   └─> asr_job_service.create_asr_job()
       └─> Supabase: INSERT INTO asr_jobs
       └─> asr_job_service.update_status() [when complete]

4. Transcript Storage
   └─> utterance_service.create_utterances_batch()
       └─> Supabase: INSERT INTO utterances (bulk)

5. Chunk Creation + Embeddings
   └─> embed_model.embed(texts) [OpenAI]
       └─> chunk_service.create_chunks_batch()
           └─> Supabase: INSERT INTO chunks with vectors

6. Semantic Search
   └─> embed_model.embed(query) [OpenAI]
       └─> chunk_service.semantic_search()
           └─> Supabase: SELECT with vector similarity

7. Summary Generation
   └─> summary_service.upsert_summary()
       └─> Supabase: UPSERT INTO summaries
```

## Integration with Existing Code

The Supabase integration coexists with your existing SQLAlchemy ORM:

### SQLAlchemy (Current)
```python
from app.data.models.base import SessionLocal
from app.data.models.meeting import Meeting

db = SessionLocal()
meeting = Meeting(title="Test")
db.add(meeting)
db.commit()
```

### Supabase (New)
```python
from app.supabase import get_supabase_client, MeetingService

client = get_supabase_client()
service = MeetingService(client)
meeting = service.create_meeting(title="Test")
```

Both can be used simultaneously during migration!

## Key Features

✅ **Complete CRUD Operations** - All models fully supported  
✅ **Batch Operations** - Efficient bulk inserts  
✅ **Vector Search** - Semantic search with pgvector  
✅ **Type Safety** - Proper type hints throughout  
✅ **Error Handling** - Graceful error management  
✅ **Well Documented** - Comprehensive docstrings  
✅ **Example Code** - Real-world usage examples  
✅ **SQL Scripts** - Database setup automation  
✅ **Admin Mode** - Bypass RLS when needed  
✅ **Relationship Queries** - Join tables efficiently  

## Environment Configuration

Required in `.env`:
```bash
# Database
DATABASE_URL=postgresql://...

# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# OpenAI (for embeddings)
OPENAI_API_KEY=...
OPENAI_EMBED_MODEL=text-embedding-3-large
```

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Copy `.env_example` to `.env` and fill in credentials
3. ✅ Run `app/supabase/sql/setup.sql` in Supabase SQL Editor
4. ✅ Test with `python app/supabase/example_usage.py`
5. ✅ Integrate services into your application code

## Support

For questions or issues:
- Check `app/supabase/README.md` for detailed documentation
- Review `app/supabase/example_usage.py` for usage patterns
- Refer to model files in `app/data/models/` for schema details

---

**Created**: October 17, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅

