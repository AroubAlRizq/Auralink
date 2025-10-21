# fetch_transcript.py
"""
Manually fetch completed transcript from AssemblyAI
and process it into your database
"""

import os
import requests
from dotenv import load_dotenv
from app.utils.database import DatabaseManager
import asyncio

load_dotenv()

def _ms_to_s(v):
    """Convert milliseconds to seconds"""
    try:
        return float(v) / 1000.0
    except Exception:
        return float(v)

async def fetch_and_process_transcript(meeting_id: str):
    """Fetch transcript from AssemblyAI and save to database"""
    
    print("=" * 70)
    print("📥 FETCHING TRANSCRIPT FROM ASSEMBLYAI")
    print("=" * 70)
    
    db = DatabaseManager()
    
    # Get the ASR job for this meeting
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    cur.execute("""
        SELECT job_id, provider, status 
        FROM asr_jobs 
        WHERE meeting_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (meeting_id,))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if not result:
        print(f"❌ No ASR job found for meeting {meeting_id}")
        return False
    
    job_id, provider, current_status = result
    
    print(f"\n📋 Meeting ID: {meeting_id}")
    print(f"🔧 Job ID: {job_id}")
    print(f"📡 Provider: {provider}")
    print(f"📊 Current Status: {current_status}")
    
    if current_status == "completed":
        print("\n⚠️  Status already 'completed' - checking if utterances exist...")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM utterances WHERE meeting_id = %s", (meeting_id,))
        count = cur.fetchone()[0]
        cur.close()
        if count > 0:
            print(f"✅ Already have {count} utterances. Nothing to do.")
            return True
        else:
            print("⚠️  No utterances found. Will fetch from AssemblyAI...")
    
    # Fetch from AssemblyAI
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("❌ ASSEMBLYAI_API_KEY not set")
        return False
    
    print(f"\n⏳ Fetching transcript from AssemblyAI...")
    
    response = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{job_id}",
        headers={"authorization": api_key}
    )
    
    if response.status_code != 200:
        print(f"❌ Error fetching transcript: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    status = data.get("status")
    
    print(f"📊 AssemblyAI Status: {status}")
    
    if status == "error":
        error_msg = data.get("error", "Unknown error")
        print(f"❌ Transcription failed: {error_msg}")
        db.update_meeting_status(meeting_id, "error")
        db.update_asr_job(job_id, status="error", raw=data, error=error_msg)
        return False
    
    if status in ["queued", "processing"]:
        print(f"⏳ Still {status}. Try again in 30 seconds.")
        return False
    
    if status == "completed":
        print(f"✅ Transcription completed!")
        
        # Parse utterances
        ulist = []
        for u in data.get("utterances", []):
            sp = u.get("speaker") or "SPEAKER"
            start = _ms_to_s(u.get("start", 0))
            end = _ms_to_s(u.get("end", start))
            text = (u.get("text") or "").strip()
            if text:
                ulist.append({
                    "speaker": sp,
                    "start_seconds": start,
                    "end_seconds": end,
                    "text": text
                })
        
        print(f"📝 Found {len(ulist)} utterances")
        
        if not ulist:
            print("⚠️  No utterances found in transcript")
            return False
        
        # Display first few utterances
        print(f"\n📄 Sample utterances:")
        for u in ulist[:3]:
            print(f"   [{u['start_seconds']:.1f}s] {u['speaker']}: {u['text'][:60]}...")
        
        # Save to database
        print(f"\n💾 Saving utterances to Supabase...")
        success = db.bulk_insert_utterances(meeting_id, ulist)
        
        if success:
            print(f"✅ Saved {len(ulist)} utterances to database")
        else:
            print(f"❌ Failed to save utterances")
            return False
        
        # Update statuses
        db.update_meeting_status(meeting_id, "asr_done")
        db.update_asr_job(job_id, status="completed", raw=data)
        
        print(f"✅ Updated meeting status to 'asr_done'")
        
        # Auto-index for RAG
        print(f"\n🔍 Auto-indexing for RAG...")
        try:
            from app.rag.indexer_service import index_transcript
            indexed = await index_transcript(meeting_id, ulist)
            print(f"✅ Indexed {indexed} chunks for RAG")
        except Exception as e:
            print(f"⚠️  Indexing failed: {e}")
            print("   (Transcription still saved successfully)")
        
        # Summary
        print("\n" + "=" * 70)
        print("🎉 SUCCESS!")
        print("=" * 70)
        print(f"✅ Transcript downloaded and saved")
        print(f"✅ {len(ulist)} utterances in database")
        print(f"✅ Ready for summarization and chat")
        print("\n📋 NEXT STEPS:")
        print(f"   1. Generate summary:")
        print(f"      python -c \"import requests; print(requests.post('http://localhost:8000/api/summarize?mode=text&meeting_id={meeting_id}').json())\"")
        print(f"\n   2. Chat with meeting:")
        print(f"      python -c \"import requests; print(requests.post('http://localhost:8000/api/chat', json={{'meeting_id':'{meeting_id}','question':'What happened?'}}).json())\"")
        print("=" * 70)
        
        return True
    
    print(f"❌ Unexpected status: {status}")
    return False

if __name__ == "__main__":
    import sys
    
    # Get meeting ID from command line or use default
    if len(sys.argv) > 1:
        meeting_id = sys.argv[1]
    else:
        meeting_id = "e6e61d70-62be-4e22-bbf5-262f09c8c758"  # Your current meeting
    
    success = asyncio.run(fetch_and_process_transcript(meeting_id))
    
    if success:
        print("\n✨ All done! Check Supabase to see your data.")
        exit(0)
    else:
        print("\n❌ Failed to fetch transcript. Check the errors above.")
        exit(1)