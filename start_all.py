# # start_all.py
# """
# Starts both the FastAPI server and the auto-poll service together.
# Just run: python start_all.py
# """

# import subprocess
# import sys
# import time
# import os
# import signal

# def main():
#     print("=" * 70)
#     print("🚀 STARTING MEETING STORYTELLING API + AUTO-POLL SERVICE")
#     print("=" * 70)
#     print()
    
#     processes = []
    
#     try:
#         # Start FastAPI server
#         print("🚀 Starting FastAPI Server...")
#         api_process = subprocess.Popen(
#             [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
#             stdout=subprocess.DEVNULL,
#             stderr=subprocess.DEVNULL
#         )
#         processes.append(("FastAPI", api_process))
#         time.sleep(3)
        
#         # Check if it started successfully
#         if api_process.poll() is not None:
#             print("❌ FastAPI server failed to start!")
#             raise Exception("FastAPI failed")
        
#         print("✅ FastAPI server started on http://localhost:8000")
#         print("📝 API Docs: http://localhost:8000/docs")
#         print()
        
#         # Start auto-poll service
#         print("🚀 Starting Auto-Poll Service...")
#         poll_process = subprocess.Popen(
#             [sys.executable, "auto_poll_service.py"],
#             stdout=subprocess.DEVNULL,
#             stderr=subprocess.DEVNULL
#         )
#         processes.append(("Auto-Poll", poll_process))
#         time.sleep(2)
        
#         # Check if it started successfully
#         if poll_process.poll() is not None:
#             print("❌ Auto-poll service failed to start!")
#             print("\n💡 Try running manually to see errors:")
#             print("   python auto_poll_service.py")
#             raise Exception("Auto-poll failed")
        
#         print("✅ Auto-poll service started")
#         print()
#         print("=" * 70)
#         print("✅ ALL SERVICES RUNNING")
#         print("=" * 70)
#         print()
#         print("💡 What's running:")
#         print("   • FastAPI server at http://localhost:8000")
#         print("   • Auto-poll checking for transcripts every 30 seconds")
#         print()
#         print("📋 To upload a video:")
#         print('   curl -X POST "http://localhost:8000/api/ingest/upload" \\')
#         print('     -F "meeting_id=new" \\')
#         print('     -F "video_file=@your_video.mp4"')
#         print()
#         print("🔄 Transcripts will be automatically:")
#         print("   • Downloaded when ready")
#         print("   • Saved to Supabase")
#         print("   • Indexed for RAG")
#         print()
#         print("📊 Monitor logs:")
#         print("   • API logs: Check terminal output")
#         print("   • Supabase: https://supabase.com/dashboard")
#         print()
#         print("⌨️  Press Ctrl+C to stop all services")
#         print("=" * 70)
#         print()
        
#         # Keep running and monitor
#         print("🔍 Services are running in background...")
#         print("   (Logs are suppressed - services running silently)")
#         print()
        
#         while True:
#             # Check if processes are still alive
#             for name, process in processes:
#                 if process.poll() is not None:
#                     print(f"\n⚠️  {name} exited with code {process.returncode}")
#                     if name == "Auto-Poll":
#                         print("\n💡 To debug, run manually:")
#                         print("   python auto_poll_service.py")
#                     raise KeyboardInterrupt
#             time.sleep(2)
            
#     except KeyboardInterrupt:
#         print("\n\n🛑 Stopping all services...")
        
#         for name, process in processes:
#             print(f"   Stopping {name}...")
#             try:
#                 process.terminate()
#                 process.wait(timeout=3)
#             except subprocess.TimeoutExpired:
#                 process.kill()
#                 process.wait()
        
#         print("\n👋 All services stopped")
#         print("=" * 70)

# if __name__ == "__main__":
#     main()