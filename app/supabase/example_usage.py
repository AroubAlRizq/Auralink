# app/supabase/example_usage.py
"""
Example usage of Supabase services for Auralink.
This file demonstrates common operations with the Supabase integration.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.supabase import (
    get_supabase_client,
    get_admin_client,
    MeetingService,
    FileService,
    ChunkService,
    SummaryService,
    UtteranceService,
    AsrJobService
)
from app_config import embed_model


def example_create_meeting():
    """Example: Create a new meeting"""
    client = get_supabase_client()
    meeting_service = MeetingService(client)
    
    meeting = meeting_service.create_meeting(
        title="Team Standup - October 17, 2025",
        video_url="https://example.com/videos/standup.mp4",
        consent=True,
        status="uploaded"
    )
    
    print(f"✓ Created meeting: {meeting['id']}")
    print(f"  Title: {meeting['title']}")
    print(f"  Status: {meeting['status']}")
    
    return meeting['id']


def example_upload_file(meeting_id: str):
    """Example: Create file metadata"""
    client = get_supabase_client()
    file_service = FileService(client)
    
    file = file_service.create_file(
        meeting_id=meeting_id,
        path="meetings/standup-oct17.mp4",
        kind="upload",
        public_url="https://storage.supabase.co/...",
        size_bytes=52428800,  # 50 MB
        mime_type="video/mp4"
    )
    
    print(f"✓ Created file record: {file['id']}")
    print(f"  Path: {file['path']}")
    print(f"  Size: {file['size_bytes'] / 1024 / 1024:.2f} MB")
    
    return file['id']


def example_create_transcript(meeting_id: str):
    """Example: Create ASR transcript utterances"""
    client = get_supabase_client()
    utterance_service = UtteranceService(client)
    
    # Sample transcript data
    utterances_data = [
        {
            "meeting_id": meeting_id,
            "speaker": "SPEAKER_0",
            "text": "Good morning everyone! Let's start with our standup.",
            "start_seconds": 0.0,
            "end_seconds": 3.5
        },
        {
            "meeting_id": meeting_id,
            "speaker": "SPEAKER_1",
            "text": "Hi! I finished the login feature yesterday.",
            "start_seconds": 3.5,
            "end_seconds": 7.0
        },
        {
            "meeting_id": meeting_id,
            "speaker": "SPEAKER_0",
            "text": "Great work! Any blockers?",
            "start_seconds": 7.0,
            "end_seconds": 9.0
        },
        {
            "meeting_id": meeting_id,
            "speaker": "SPEAKER_1",
            "text": "No blockers. Today I'll work on the dashboard.",
            "start_seconds": 9.0,
            "end_seconds": 12.5
        }
    ]
    
    utterances = utterance_service.create_utterances_batch(utterances_data)
    
    print(f"✓ Created {len(utterances)} utterances")
    
    # Get full transcript
    transcript = utterance_service.get_full_transcript(
        meeting_id=meeting_id,
        include_timestamps=True
    )
    print("\n📝 Transcript:")
    print(transcript)
    
    return len(utterances)


def example_create_chunks_with_embeddings(meeting_id: str):
    """Example: Create text chunks with embeddings"""
    client = get_supabase_client()
    chunk_service = ChunkService(client)
    
    # Sample chunks
    chunk_texts = [
        "Good morning everyone! Let's start with our standup. Hi! I finished the login feature yesterday.",
        "Great work! Any blockers? No blockers. Today I'll work on the dashboard."
    ]
    
    # Generate embeddings
    print("🔄 Generating embeddings...")
    embeddings = embed_model.embed(chunk_texts)
    
    # Create chunks with embeddings
    chunks_data = [
        {
            "meeting_id": meeting_id,
            "text": chunk_texts[0],
            "start_seconds": 0.0,
            "end_seconds": 7.0,
            "speaker": "SPEAKER_0",
            "topic": "asr",
            "embedding": embeddings[0]
        },
        {
            "meeting_id": meeting_id,
            "text": chunk_texts[1],
            "start_seconds": 7.0,
            "end_seconds": 12.5,
            "speaker": "SPEAKER_1",
            "topic": "asr",
            "embedding": embeddings[1]
        }
    ]
    
    chunks = chunk_service.create_chunks_batch(chunks_data)
    
    print(f"✓ Created {len(chunks)} chunks with embeddings")
    
    return len(chunks)


def example_semantic_search(meeting_id: str):
    """Example: Perform semantic search"""
    client = get_supabase_client()
    chunk_service = ChunkService(client)
    
    # Query
    query = "What did the team discuss about the dashboard?"
    
    print(f"\n🔍 Searching: '{query}'")
    print("🔄 Generating query embedding...")
    
    query_embedding = embed_model.embed([query])[0]
    
    # Perform semantic search
    results = chunk_service.semantic_search(
        meeting_id=meeting_id,
        query_embedding=query_embedding,
        limit=3
    )
    
    print(f"\n✓ Found {len(results)} relevant chunks:")
    for i, result in enumerate(results, 1):
        similarity = result.get('similarity', 0)
        print(f"\n  {i}. [{result['start_seconds']:.2f}s - {result['end_seconds']:.2f}s]")
        print(f"     Similarity: {similarity:.4f}")
        print(f"     Text: {result['text'][:100]}...")


def example_create_summary(meeting_id: str):
    """Example: Create meeting summary"""
    client = get_supabase_client()
    summary_service = SummaryService(client)
    
    summary_data = {
        "title": "Team Standup - October 17, 2025",
        "overview": "Daily standup meeting discussing progress and plans.",
        "participants": [
            "SPEAKER_0 (Moderator)",
            "SPEAKER_1 (Developer)"
        ],
        "key_points": [
            "Login feature completed",
            "Dashboard work planned for today"
        ],
        "action_items": [
            {
                "owner": "SPEAKER_1",
                "task": "Work on dashboard implementation",
                "due_date": "2025-10-18"
            }
        ],
        "decisions": [],
        "next_meeting": "2025-10-18"
    }
    
    summary = summary_service.upsert_summary(
        meeting_id=meeting_id,
        payload=summary_data
    )
    
    print(f"✓ Created summary for meeting")
    print(f"  Title: {summary_data['title']}")
    print(f"  Key Points: {len(summary_data['key_points'])}")
    print(f"  Action Items: {len(summary_data['action_items'])}")


def example_track_asr_job(meeting_id: str):
    """Example: Track ASR processing job"""
    client = get_supabase_client()
    asr_job_service = AsrJobService(client)
    
    # Create ASR job
    job = asr_job_service.create_asr_job(
        job_id="assemblyai_abc123xyz",
        meeting_id=meeting_id,
        provider="assemblyai",
        callback_url="https://api.example.com/webhooks/asr",
        status="queued"
    )
    
    print(f"✓ Created ASR job: {job['id']}")
    print(f"  Provider: {job['provider']}")
    print(f"  Status: {job['status']}")
    
    # Simulate status updates
    print("\n🔄 Processing...")
    asr_job_service.update_status(job['id'], "processing")
    
    print("✓ Job status updated to: processing")
    
    # Mark as completed
    asr_job_service.mark_completed(job['id'])
    print("✓ Job marked as completed")


def example_query_meeting_data(meeting_id: str):
    """Example: Query meeting with all relations"""
    client = get_supabase_client()
    meeting_service = MeetingService(client)
    
    # Get meeting with all related data
    meeting = meeting_service.get_meeting_with_relations(meeting_id)
    
    print(f"\n📊 Meeting Summary:")
    print(f"  ID: {meeting['id']}")
    print(f"  Title: {meeting['title']}")
    print(f"  Status: {meeting['status']}")
    print(f"  Files: {len(meeting.get('files', []))}")
    print(f"  Utterances: {len(meeting.get('utterances', []))}")
    print(f"  Chunks: {len(meeting.get('chunks', []))}")
    print(f"  ASR Jobs: {len(meeting.get('asr_jobs', []))}")


def run_complete_example():
    """Run a complete example workflow"""
    print("=" * 60)
    print("Supabase Integration Example - Complete Workflow")
    print("=" * 60)
    
    try:
        # Step 1: Create meeting
        print("\n1️⃣  Creating meeting...")
        meeting_id = example_create_meeting()
        
        # Step 2: Upload file
        print("\n2️⃣  Creating file record...")
        example_upload_file(meeting_id)
        
        # Step 3: Track ASR job
        print("\n3️⃣  Tracking ASR job...")
        example_track_asr_job(meeting_id)
        
        # Step 4: Create transcript
        print("\n4️⃣  Creating transcript...")
        example_create_transcript(meeting_id)
        
        # Step 5: Create chunks with embeddings
        print("\n5️⃣  Creating chunks with embeddings...")
        example_create_chunks_with_embeddings(meeting_id)
        
        # Step 6: Perform semantic search
        print("\n6️⃣  Performing semantic search...")
        example_semantic_search(meeting_id)
        
        # Step 7: Create summary
        print("\n7️⃣  Creating summary...")
        example_create_summary(meeting_id)
        
        # Step 8: Query all data
        print("\n8️⃣  Querying meeting data...")
        example_query_meeting_data(meeting_id)
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run individual examples or complete workflow
    run_complete_example()

