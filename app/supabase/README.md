# Supabase Integration

This module provides a complete integration between your ORM models and Supabase PostgreSQL database with pgvector support.

## Setup

### 1. Environment Variables

Copy `.env_example` to `.env` and fill in your Supabase credentials:

```bash
# Database Connection
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Supabase Configuration
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_KEY=[YOUR-ANON-KEY]
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SERVICE-ROLE-KEY]
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Schema

Run the SQL schema files in your Supabase SQL editor:
1. First, enable the pgvector extension
2. Create tables using `schemas/db.sql`
3. Create the vector search function using `app/supabase/sql/match_chunks.sql`

## Usage

### Basic Usage

```python
from app.supabase import (
    get_supabase_client,
    MeetingService,
    FileService,
    ChunkService,
    SummaryService,
    UtteranceService,
    AsrJobService
)

# Get Supabase client
client = get_supabase_client()

# Initialize services
meeting_service = MeetingService(client)
file_service = FileService(client)
chunk_service = ChunkService(client)
summary_service = SummaryService(client)
utterance_service = UtteranceService(client)
asr_job_service = AsrJobService(client)
```

### Creating a Meeting

```python
# Create a new meeting
meeting = meeting_service.create_meeting(
    title="Team Standup - Oct 17, 2025",
    video_url="https://example.com/video.mp4",
    consent=True
)
print(f"Created meeting: {meeting['id']}")
```

### Working with Files

```python
# Upload file metadata
file = file_service.create_file(
    meeting_id=meeting['id'],
    path="meetings/video.mp4",
    kind="upload",
    public_url="https://storage.supabase.co/...",
    size_bytes=1024000,
    mime_type="video/mp4"
)
```

### Creating Utterances (ASR Transcripts)

```python
# Create transcript utterances
utterances_data = [
    {
        "meeting_id": meeting['id'],
        "speaker": "SPEAKER_0",
        "text": "Good morning everyone!",
        "start_seconds": 0.0,
        "end_seconds": 2.5
    },
    {
        "meeting_id": meeting['id'],
        "speaker": "SPEAKER_1",
        "text": "Hi! Let's get started.",
        "start_seconds": 2.5,
        "end_seconds": 5.0
    }
]

utterances = utterance_service.create_utterances_batch(utterances_data)
```

### Creating Chunks with Embeddings

```python
from app_config import embed_model

# Create text chunks
text = "Good morning everyone! Hi! Let's get started."
embeddings = embed_model.embed([text])

chunk = chunk_service.create_chunk(
    meeting_id=meeting['id'],
    text=text,
    start_seconds=0.0,
    end_seconds=5.0,
    speaker="SPEAKER_0",
    topic="asr",
    embedding=embeddings[0]
)
```

### Semantic Search

```python
# Perform semantic search
query = "What was discussed about the project timeline?"
query_embedding = embed_model.embed([query])[0]

results = chunk_service.semantic_search(
    meeting_id=meeting['id'],
    query_embedding=query_embedding,
    limit=5
)

for result in results:
    print(f"[{result['start_seconds']:.2f}s] {result['text']}")
```

### Creating/Updating Summaries

```python
# Create or update meeting summary
summary_data = {
    "title": "Team Standup Summary",
    "overview": "Discussed project progress and blockers",
    "action_items": [
        "John to review PR #123",
        "Sarah to update documentation"
    ],
    "key_decisions": [
        "Decided to extend deadline by 2 days"
    ]
}

summary = summary_service.upsert_summary(
    meeting_id=meeting['id'],
    payload=summary_data
)
```

### Tracking ASR Jobs

```python
# Create ASR job tracking
asr_job = asr_job_service.create_asr_job(
    job_id="assemblyai_abc123",
    meeting_id=meeting['id'],
    provider="assemblyai",
    callback_url="https://api.example.com/webhook/asr",
    status="queued"
)

# Update job status
asr_job_service.update_status(
    job_id="assemblyai_abc123",
    status="completed"
)
```

### Querying Data

```python
# Get meeting with all relations
meeting_full = meeting_service.get_meeting_with_relations(meeting['id'])
print(f"Files: {len(meeting_full['files'])}")
print(f"Utterances: {len(meeting_full['utterances'])}")
print(f"Chunks: {len(meeting_full['chunks'])}")

# Get recent meetings
recent = meeting_service.get_recent_meetings(limit=10)

# Search utterances
search_results = utterance_service.search_text(
    meeting_id=meeting['id'],
    search_term="timeline",
    case_sensitive=False
)

# Get full transcript
transcript = utterance_service.get_full_transcript(
    meeting_id=meeting['id'],
    include_timestamps=True
)
print(transcript)
```

## Services Overview

### MeetingService
- `create_meeting()` - Create new meeting
- `get_meeting()` - Get meeting by ID
- `update_status()` - Update meeting status
- `get_by_status()` - Filter by status
- `get_recent_meetings()` - Get recent meetings
- `get_meeting_with_relations()` - Get meeting with all related data
- `delete_meeting()` - Delete meeting (cascades)

### FileService
- `create_file()` - Create file record
- `get_files_by_meeting()` - Get all files for meeting
- `get_files_by_kind()` - Filter files by type
- `update_public_url()` - Update file URL
- `delete_file()` - Delete file record

### ChunkService
- `create_chunk()` - Create text chunk with embedding
- `create_chunks_batch()` - Batch create chunks
- `get_chunks_by_meeting()` - Get all chunks
- `get_chunks_by_time_range()` - Filter by time
- `get_chunks_by_topic()` - Filter by topic
- `semantic_search()` - Vector similarity search
- `update_embedding()` - Update chunk embedding
- `delete_chunks_by_meeting()` - Delete all chunks for meeting

### SummaryService
- `create_summary()` - Create summary
- `get_summary()` - Get summary by meeting ID
- `update_summary()` - Update summary
- `upsert_summary()` - Create or update summary
- `get_summary_field()` - Get specific field from payload
- `delete_summary()` - Delete summary

### UtteranceService
- `create_utterance()` - Create single utterance
- `create_utterances_batch()` - Batch create utterances
- `get_utterances_by_meeting()` - Get all utterances
- `get_utterances_by_speaker()` - Filter by speaker
- `get_utterances_by_time_range()` - Filter by time
- `get_full_transcript()` - Get formatted transcript
- `search_text()` - Text search in utterances
- `delete_utterances_by_meeting()` - Delete all utterances

### AsrJobService
- `create_asr_job()` - Create ASR job record
- `get_asr_job()` - Get job by ID
- `get_jobs_by_meeting()` - Get all jobs for meeting
- `get_jobs_by_status()` - Filter by status
- `get_jobs_by_provider()` - Filter by provider
- `update_status()` - Update job status
- `mark_completed()` - Mark job as completed
- `mark_error()` - Mark job as failed
- `delete_asr_job()` - Delete job record

## Admin vs User Client

```python
from app.supabase import get_supabase_client, get_admin_client

# User-level client (respects Row Level Security)
user_client = get_supabase_client()

# Admin client (bypasses RLS - use with caution)
admin_client = get_admin_client()

# Use admin client for operations that need elevated permissions
meeting_service = MeetingService(admin_client)
```

## Error Handling

```python
try:
    meeting = meeting_service.create_meeting(
        title="My Meeting",
        consent=True
    )
except Exception as e:
    print(f"Error creating meeting: {e}")
```

## Best Practices

1. **Use batch operations** for multiple records (e.g., `create_chunks_batch()`)
2. **Reuse client instances** - create once, use throughout your application
3. **Enable proper indexes** on frequently queried columns
4. **Use semantic search** for natural language queries
5. **Implement proper error handling** for all database operations
6. **Use admin client sparingly** - only for operations that truly need it

## Migration from SQLAlchemy

If you have existing SQLAlchemy code, you can gradually migrate:

```python
# Old SQLAlchemy way
from app.data.models.base import SessionLocal
from app.data.models.meeting import Meeting

db = SessionLocal()
meeting = Meeting(title="Test", consent=True)
db.add(meeting)
db.commit()

# New Supabase way
from app.supabase import get_supabase_client, MeetingService

client = get_supabase_client()
meeting_service = MeetingService(client)
meeting = meeting_service.create_meeting(title="Test", consent=True)
```

Both approaches can coexist in your application during migration.

