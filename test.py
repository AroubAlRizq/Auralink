# debug_pipeline.py
import asyncio
from app.utils.database import DatabaseManager

async def debug_pipeline(meeting_id: str):
    db = DatabaseManager()
    
    print("🔍 DEBUGGING PIPELINE")
    print("=" * 50)
    
    # 1. Check meeting exists
    meeting = db.get_meeting(meeting_id)
    print(f"1. Meeting exists: {meeting is not None}")
    if meeting:
        print(f"   Status: {meeting.get('status')}")
        print(f"   Video URL: {meeting.get('video_url')}")
    
    # 2. Check ASR jobs
    query = "SELECT COUNT(*) FROM asr_jobs WHERE meeting_id = %s"
    result = db.client.execute_query(query, (meeting_id,))
    asr_count = result[0][0] if result else 0
    print(f"2. ASR jobs: {asr_count}")
    
    # 3. Check utterances
    utterances = db.get_utterances_by_meeting(meeting_id)
    print(f"3. Utterances: {len(utterances)}")
    if utterances:
        print(f"   First utterance: {utterances[0]}")
    
    # 4. Check summaries
    summary = db.get_summary(meeting_id)
    print(f"4. Summary exists: {summary is not None}")
    if summary:
        print(f"   Executive summary bullets: {len(summary.get('executive_summary', []))}")
    
    # 5. Check chunks
    query = "SELECT COUNT(*) FROM chunks WHERE meeting_id = %s"
    result = db.client.execute_query(query, (meeting_id,))
    chunk_count = result[0][0] if result else 0
    print(f"5. Chunks: {chunk_count}")
    
    # 6. Check if chunks table exists
    try:
        query = "SELECT COUNT(*) FROM chunks"
        result = db.client.execute_query(query)
        print(f"6. Chunks table exists: True")
    except Exception as e:
        print(f"6. Chunks table exists: False - {e}")
    
    print("=" * 50)
    
    if len(utterances) == 0:
        print("❌ PROBLEM: No utterances found!")
        print("   This means the ASR webhook didn't save utterances")
        print("   Check your ASR provider logs")
    elif chunk_count == 0:
        print("❌ PROBLEM: No chunks found!")
        print("   This means the indexing failed")
        print("   Run: python reindex_meeting.py <meeting_id>")
    else:
        print("✅ Pipeline working correctly!")

if __name__ == "__main__":
    import sys
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else "8e34ca25-7bff-4107-9da6-ffd0617bfbee"
    asyncio.run(debug_pipeline(meeting_id))