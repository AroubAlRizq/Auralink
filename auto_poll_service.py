# auto_poll_service.py
"""
Background service that automatically polls AssemblyAI for completed transcripts
and processes them without manual intervention.

Run this alongside your FastAPI server:
    python auto_poll_service.py
"""

import os
import sys
import time
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Configuration
POLL_INTERVAL = 30  # Check every 30 seconds
MAX_AGE_HOURS = 24  # Only check jobs from last 24 hours

def _ms_to_s(v):
    """Convert milliseconds to seconds"""
    try:
        return float(v) / 1000.0
    except Exception:
        return float(v)

def get_pending_jobs():
    """Get all ASR jobs that are still processing"""
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        # Find jobs that are processing and less than 24 hours old
        cur.execute("""
            SELECT job_id, meeting_id, provider
            FROM asr_jobs
            WHERE status = 'processing'
            AND provider = 'assemblyai'
            AND created_at > NOW() - INTERVAL '%s hours'
            ORDER BY created_at DESC
        """ % MAX_AGE_HOURS)
        
        jobs = cur.fetchall()
        cur.close()
        conn.close()
        
        return jobs
    except Exception as e:
        print(f"  ⚠️  Error getting pending jobs: {e}")
        return []

async def process_completed_transcript(job_id: str, meeting_id: str, data: dict):
    """Process a completed transcript"""
    try:
        from app.utils.database import DatabaseManager
        from app.rag.indexer_service import index_transcript
        
        db = DatabaseManager()
        
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
        
        if not ulist:
            print(f"  ⚠️  No utterances found for {meeting_id}")
            return False
        
        # Save utterances
        print(f"  💾 Saving {len(ulist)} utterances...")
        db.bulk_insert_utterances(meeting_id, ulist)
        
        # Update statuses
        db.update_meeting_status(meeting_id, "asr_done")
        db.update_asr_job(job_id, status="completed", raw=data)
        
        # Auto-index
        print(f"  🔍 Auto-indexing for RAG...")
        try:
            indexed = await index_transcript(meeting_id, ulist)
            print(f"  ✅ Indexed {indexed} chunks")
        except Exception as e:
            print(f"  ⚠️  Indexing failed: {e}")
        
        print(f"  🎉 Meeting {meeting_id[:8]}... ready for summarization!")
        return True
        
    except Exception as e:
        print(f"  ❌ Error processing transcript: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_job(job_id: str, meeting_id: str):
    """Check a single job with AssemblyAI"""
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("❌ ASSEMBLYAI_API_KEY not set")
        return False
    
    try:
        import requests
        response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{job_id}",
            headers={"authorization": api_key},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"  ⚠️  Error checking job {job_id}: {response.status_code}")
            return False
        
        data = response.json()
        status = data.get("status")
        
        if status == "completed":
            print(f"\n✅ Transcript completed: {meeting_id[:8]}...")
            await process_completed_transcript(job_id, meeting_id, data)
            return True
        
        elif status == "error":
            from app.utils.database import DatabaseManager
            error_msg = data.get("error", "Unknown error")
            print(f"\n❌ Transcription failed for {meeting_id[:8]}...: {error_msg}")
            db = DatabaseManager()
            db.update_meeting_status(meeting_id, "error")
            db.update_asr_job(job_id, status="error", raw=data, error=error_msg)
            return True
        
        # Still processing - no action needed
        return False
        
    except Exception as e:
        print(f"  ⚠️  Error checking job {job_id}: {e}")
        return False

async def poll_once():
    """Single poll cycle - check all pending jobs"""
    jobs = get_pending_jobs()
    
    if not jobs:
        return 0
    
    print(f"\n🔍 Checking {len(jobs)} pending job(s)...")
    
    completed = 0
    for job_id, meeting_id, provider in jobs:
        if await check_job(job_id, meeting_id):
            completed += 1
        await asyncio.sleep(1)  # Small delay between checks
    
    return completed

async def main():
    """Main polling loop"""
    print("=" * 70)
    print("🤖 AUTO-POLL SERVICE STARTED")
    print("=" * 70)
    print(f"⏱️  Poll interval: {POLL_INTERVAL} seconds")
    print(f"📅 Max job age: {MAX_AGE_HOURS} hours")
    print(f"🔧 Provider: AssemblyAI")
    print("\n💡 This service will automatically:")
    print("   • Check for completed transcripts")
    print("   • Download and save utterances")
    print("   • Auto-index for RAG")
    print("   • Update meeting status")
    print("\n⌨️  Press Ctrl+C to stop")
    print("=" * 70)
    
    # Test database connection
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        conn.close()
        print("✅ Database connection OK")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Fix your DATABASE_URL and try again")
        return
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{timestamp}] Cycle #{cycle}")
            
            try:
                completed = await poll_once()
                
                if completed > 0:
                    print(f"✅ Processed {completed} completed transcript(s)")
                else:
                    print(f"⏳ No completed transcripts yet")
            except Exception as e:
                print(f"❌ Error in poll cycle: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"💤 Sleeping for {POLL_INTERVAL} seconds...")
            await asyncio.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Auto-poll service stopped")
        print("=" * 70)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Configuration
POLL_INTERVAL = 30  # Check every 30 seconds
MAX_AGE_HOURS = 24  # Only check jobs from last 24 hours

def _ms_to_s(v):
    """Convert milliseconds to seconds"""
    try:
        return float(v) / 1000.0
    except Exception:
        return float(v)

def get_pending_jobs():
    """Get all ASR jobs that are still processing"""
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    # Find jobs that are processing and less than 24 hours old
    cur.execute("""
        SELECT job_id, meeting_id, provider
        FROM asr_jobs
        WHERE status = 'processing'
        AND provider = 'assemblyai'
        AND created_at > NOW() - INTERVAL '%s hours'
        ORDER BY created_at DESC
    """ % MAX_AGE_HOURS)
    
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    
    return jobs

async def process_completed_transcript(job_id: str, meeting_id: str, data: dict):
    """Process a completed transcript"""
    db = DatabaseManager()
    
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
    
    if not ulist:
        print(f"  ⚠️  No utterances found for {meeting_id}")
        return False
    
    # Save utterances
    print(f"  💾 Saving {len(ulist)} utterances...")
    db.bulk_insert_utterances(meeting_id, ulist)
    
    # Update statuses
    db.update_meeting_status(meeting_id, "asr_done")
    db.update_asr_job(job_id, status="completed", raw=data)
    
    # Auto-index
    print(f"  🔍 Auto-indexing for RAG...")
    try:
        indexed = await index_transcript(meeting_id, ulist)
        print(f"  ✅ Indexed {indexed} chunks")
    except Exception as e:
        print(f"  ⚠️  Indexing failed: {e}")
    
    print(f"  🎉 Meeting {meeting_id[:8]}... ready for summarization!")
    return True

async def check_job(job_id: str, meeting_id: str):
    """Check a single job with AssemblyAI"""
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("❌ ASSEMBLYAI_API_KEY not set")
        return False
    
    try:
        response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{job_id}",
            headers={"authorization": api_key},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"  ⚠️  Error checking job {job_id}: {response.status_code}")
            return False
        
        data = response.json()
        status = data.get("status")
        
        if status == "completed":
            print(f"\n✅ Transcript completed: {meeting_id[:8]}...")
            await process_completed_transcript(job_id, meeting_id, data)
            return True
        
        elif status == "error":
            error_msg = data.get("error", "Unknown error")
            print(f"\n❌ Transcription failed for {meeting_id[:8]}...: {error_msg}")
            db = DatabaseManager()
            db.update_meeting_status(meeting_id, "error")
            db.update_asr_job(job_id, status="error", raw=data, error=error_msg)
            return True
        
        # Still processing - no action needed
        return False
        
    except Exception as e:
        print(f"  ⚠️  Error checking job {job_id}: {e}")
        return False

async def poll_once():
    """Single poll cycle - check all pending jobs"""
    jobs = get_pending_jobs()
    
    if not jobs:
        return 0
    
    print(f"\n🔍 Checking {len(jobs)} pending job(s)...")
    
    completed = 0
    for job_id, meeting_id, provider in jobs:
        if await check_job(job_id, meeting_id):
            completed += 1
        await asyncio.sleep(1)  # Small delay between checks
    
    return completed

async def main():
    """Main polling loop"""
    print("=" * 70)
    print("🤖 AUTO-POLL SERVICE STARTED")
    print("=" * 70)
    print(f"⏱️  Poll interval: {POLL_INTERVAL} seconds")
    print(f"📅 Max job age: {MAX_AGE_HOURS} hours")
    print(f"🔧 Provider: AssemblyAI")
    print("\n💡 This service will automatically:")
    print("   • Check for completed transcripts")
    print("   • Download and save utterances")
    print("   • Auto-index for RAG")
    print("   • Update meeting status")
    print("\n⌨️  Press Ctrl+C to stop")
    print("=" * 70)
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{timestamp}] Cycle #{cycle}")
            
            completed = await poll_once()
            
            if completed > 0:
                print(f"✅ Processed {completed} completed transcript(s)")
            else:
                print(f"⏳ No completed transcripts yet")
            
            print(f"💤 Sleeping for {POLL_INTERVAL} seconds...")
            await asyncio.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Auto-poll service stopped")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())