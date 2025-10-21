# start_all.ps1
# Starts both FastAPI server and auto-poll service
# Run: .\start_all.ps1

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "🚀 STARTING MEETING STORYTELLING API + AUTO-POLL SERVICE" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Start FastAPI server in background
Write-Host "🚀 Starting FastAPI server..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

Start-Sleep -Seconds 3
Write-Host "✅ FastAPI server started on http://localhost:8000" -ForegroundColor Green
Write-Host "📝 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

# Start auto-poll service in background
Write-Host "🚀 Starting Auto-Poll service..." -ForegroundColor Yellow
$pollJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python auto_poll_service.py
}

Start-Sleep -Seconds 2
Write-Host "✅ Auto-poll service started" -ForegroundColor Green
Write-Host ""

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "✅ ALL SERVICES RUNNING" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

Write-Host "💡 What's running:" -ForegroundColor Yellow
Write-Host "   • FastAPI server at http://localhost:8000" -ForegroundColor White
Write-Host "   • Auto-poll checking for transcripts every 30 seconds" -ForegroundColor White
Write-Host ""

Write-Host "📋 To upload a video:" -ForegroundColor Yellow
Write-Host '   $videoPath = "C:\path\to\video.mp4"' -ForegroundColor White
Write-Host '   curl.exe -X POST "http://localhost:8000/api/ingest/upload" `' -ForegroundColor White
Write-Host '     -F "meeting_id=new" `' -ForegroundColor White
Write-Host '     -F "video_file=@$videoPath"' -ForegroundColor White
Write-Host ""

Write-Host "🔄 Transcripts will be automatically:" -ForegroundColor Yellow
Write-Host "   • Downloaded when ready" -ForegroundColor White
Write-Host "   • Saved to Supabase" -ForegroundColor White
Write-Host "   • Indexed for RAG" -ForegroundColor White
Write-Host ""

Write-Host "⌨️  Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Monitor jobs
try {
    while ($true) {
        # Show live output from both jobs
        Receive-Job -Job $apiJob -ErrorAction SilentlyContinue
        Receive-Job -Job $pollJob -ErrorAction SilentlyContinue
        
        # Check if jobs are still running
        if ($apiJob.State -ne "Running") {
            Write-Host "`n❌ FastAPI server stopped!" -ForegroundColor Red
            break
        }
        if ($pollJob.State -ne "Running") {
            Write-Host "`n❌ Auto-poll service stopped!" -ForegroundColor Red
            break
        }
        
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`n🛑 Stopping all services..." -ForegroundColor Yellow
    Stop-Job -Job $apiJob, $pollJob
    Remove-Job -Job $apiJob, $pollJob -Force
    Write-Host "👋 All services stopped" -ForegroundColor Green
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 69) -ForegroundColor Cyan
}