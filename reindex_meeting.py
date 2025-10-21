# reindex_meeting.py
import asyncio
import sys
from app.utils.database import DatabaseManager
from app.rag.indexer_service import index_transcript, index_summary

async def reindex_meeting(meeting_id: str):
    """Re-index transcript and summary for a meeting"""
    db = DatabaseManager()
    
    print(f"🔍 Fetching data for meeting: {meeting_id}")
    
    # Get utterances
    utterances = db.get_utterances_by_meeting(meeting_id)
    print(f"📝 Found {len(utterances)} utterances")
    
    # Get summary
    summary = db.get_summary(meeting_id)
    print(f"📋 Found summary: {summary is not None}")
    
    if not utterances and not summary:
        print("❌ No data found to index!")
        return
    
    # Index transcript
    if utterances:
        print("\n🔄 Indexing transcript...")
        try:
            count = await index_transcript(meeting_id, utterances)
            print(f"✅ Indexed {count} transcript chunks")
        except Exception as e:
            print(f"❌ Failed to index transcript: {e}")
            import traceback
            traceback.print_exc()
    
    # Index summary
    if summary:
        print("\n🔄 Indexing summary...")
        try:
            count = await index_summary(meeting_id, summary)
            print(f"✅ Indexed {count} summary chunks")
        except Exception as e:
            print(f"❌ Failed to index summary: {e}")
            import traceback
            traceback.print_exc()
    
    # Verify chunks were created
    print("\n🔍 Verifying chunks in database...")
    query = "SELECT COUNT(*) FROM chunks WHERE meeting_id = %s"
    result = db.client.execute_query(query, (meeting_id,))
    chunk_count = result[0][0] if result else 0
    print(f"📊 Total chunks in database: {chunk_count}")
    
    if chunk_count > 0:
        print("✅ Indexing successful!")
    else:
        print("❌ No chunks were created - check the errors above")

if __name__ == "__main__":
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else "e6e61d70-62be-4e22-bbf5-262f09c8c758"
    asyncio.run(reindex_meeting(meeting_id))