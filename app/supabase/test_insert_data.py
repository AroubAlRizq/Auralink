# app/supabase/test_insert_data.py
"""
Test script to insert sample data and verify Supabase REST API works.
This will create a test meeting and retrieve it to confirm the connection.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app.supabase import (
    get_supabase_client,
    MeetingService,
    FileService,
    ChunkService,
    SummaryService
)

load_dotenv()


def test_insert_and_retrieve():
    """Test inserting and retrieving data from Supabase"""
    
    print("=" * 60)
    print("SUPABASE REST API TEST - INSERT & RETRIEVE DATA")
    print("=" * 60)
    
    try:
        # Get Supabase client
        print("\n1️⃣  Connecting to Supabase...")
        client = get_supabase_client()
        print("   ✓ Connected successfully")
        
        # Initialize services
        meeting_service = MeetingService(client)
        file_service = FileService(client)
        chunk_service = ChunkService(client)
        summary_service = SummaryService(client)
        
        # Test 1: Create a meeting
        print("\n2️⃣  Creating test meeting...")
        meeting = meeting_service.create_meeting(
            title="Test Meeting - Supabase Connection Test",
            video_url="https://example.com/test-video.mp4",
            consent=True,
            status="uploaded"
        )
        meeting_id = meeting['id']
        print(f"   ✓ Meeting created!")
        print(f"     ID: {meeting_id}")
        print(f"     Title: {meeting['title']}")
        print(f"     Status: {meeting['status']}")
        
        # Test 2: Retrieve the meeting
        print("\n3️⃣  Retrieving meeting from database...")
        retrieved = meeting_service.get_meeting(meeting_id)
        if retrieved:
            print(f"   ✓ Meeting retrieved successfully!")
            print(f"     ID: {retrieved['id']}")
            print(f"     Title: {retrieved['title']}")
        else:
            print("   ✗ Failed to retrieve meeting")
            return False
        
        # Test 3: Create a file record
        print("\n4️⃣  Creating file record...")
        file_record = file_service.create_file(
            meeting_id=meeting_id,
            path="test/video.mp4",
            kind="upload",
            public_url="https://example.com/test-video.mp4",
            size_bytes=1024000,
            mime_type="video/mp4"
        )
        print(f"   ✓ File record created!")
        print(f"     ID: {file_record['id']}")
        print(f"     Path: {file_record['path']}")
        
        # Test 4: Create chunks without embeddings (for now)
        print("\n5️⃣  Creating test chunks...")
        chunks_data = [
            {
                "meeting_id": meeting_id,
                "speaker": "SPEAKER_0",
                "start_seconds": 0.0,
                "end_seconds": 30.0,
                "topic": "test",
                "text": "This is a test chunk from the first 30 seconds.",
                "embedding": None  # No embedding for now
            },
            {
                "meeting_id": meeting_id,
                "speaker": "SPEAKER_1",
                "start_seconds": 30.0,
                "end_seconds": 60.0,
                "topic": "test",
                "text": "This is a test chunk from 30 to 60 seconds.",
                "embedding": None
            }
        ]
        
        chunks = chunk_service.create_chunks_batch(chunks_data)
        print(f"   ✓ Created {len(chunks)} chunks!")
        for i, chunk in enumerate(chunks, 1):
            print(f"     Chunk {i}: {chunk['text'][:50]}...")
        
        # Test 5: Create a summary
        print("\n6️⃣  Creating test summary...")
        summary_payload = {
            "title": "Test Meeting Summary",
            "overview": "This is a test summary to verify Supabase connection.",
            "key_points": [
                "Connection test successful",
                "Data insertion working",
                "REST API functional"
            ],
            "test_metadata": {
                "test_run": True,
                "timestamp": "2025-10-17"
            }
        }
        
        summary = summary_service.upsert_summary(
            meeting_id=meeting_id,
            payload=summary_payload
        )
        print(f"   ✓ Summary created!")
        print(f"     Title: {summary_payload['title']}")
        print(f"     Key Points: {len(summary_payload['key_points'])}")
        
        # Test 6: Query all data for this meeting
        print("\n7️⃣  Querying all related data...")
        meeting_full = meeting_service.get_meeting_with_relations(meeting_id)
        
        if meeting_full:
            print(f"   ✓ Retrieved meeting with all relations!")
            print(f"     Files: {len(meeting_full.get('files', []))}")
            print(f"     Chunks: {len(meeting_full.get('chunks', []))}")
            print(f"     Summaries: {len(meeting_full.get('summaries', []))}")
        
        # Test 7: Update meeting status
        print("\n8️⃣  Updating meeting status...")
        updated = meeting_service.update_status(meeting_id, "summarized")
        print(f"   ✓ Status updated to: {updated['status']}")
        
        # Test 8: Get recent meetings
        print("\n9️⃣  Querying recent meetings...")
        recent = meeting_service.get_recent_meetings(limit=5)
        print(f"   ✓ Found {len(recent)} recent meeting(s)")
        for mtg in recent:
            print(f"     - {mtg['title']} ({mtg['status']})")
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\n📊 Test Results:")
        print(f"   Meeting ID: {meeting_id}")
        print(f"   Files Created: 1")
        print(f"   Chunks Created: {len(chunks)}")
        print(f"   Summary Created: Yes")
        print(f"   Status: {updated['status']}")
        print("\n🎉 Your Supabase REST API connection is working perfectly!")
        print(f"\n💡 Check your Supabase Dashboard:")
        print(f"   → Table Editor → meetings → You should see your test meeting")
        print(f"   → SQL Editor → Run: SELECT * FROM meetings WHERE id = '{meeting_id}'")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you ran the SQL setup in Supabase Dashboard")
        print("2. Check your .env file has correct credentials")
        print("3. Verify tables exist: Go to Supabase → Table Editor")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_insert_and_retrieve()
    sys.exit(0 if success else 1)

