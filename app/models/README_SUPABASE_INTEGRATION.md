# Video Audio Summarizer - Supabase Integration

## Overview

The `video_audio_summarizer.py` now automatically integrates with Supabase to track meeting processing and store results.

## How It Works

When you process a video with a `title` parameter, the system automatically:

1. **Creates a meeting record** in Supabase `meetings` table with:
   - `id`: Auto-generated UUID
   - `title`: Your meeting title
   - `video_url`: Public URL to the video (if provided)
   - `consent`: User consent flag
   - `status`: Initially set to `"processing"`
   - `created_at`: Timestamp of creation

2. **Updates status during processing**:
   - `"processing"` → While analyzing video/audio
   - `"summarized"` → When complete
   - `"error"` → If processing fails

3. **Stores the summary** in Supabase `summaries` table with:
   - Complete summary text
   - Per-window narrations
   - File paths to artifacts

## Usage

### Option 1: CLI with Supabase

```bash
python -m app.models.video_audio_summarizer \
  --video path/to/video.mp4 \
  --title "Q4 Planning Meeting" \
  --video-url "https://storage.example.com/video.mp4" \
  --consent
```

### Option 2: Python API

```python
from app.models.video_audio_summarizer import summarize_video

result = summarize_video(
    video_path="path/to/video.mp4",
    title="Q4 Planning Meeting",
    video_url="https://storage.example.com/video.mp4",
    consent=True
)

print(f"Meeting ID: {result['meeting_id']}")
print(f"Status: summarized")
```

### Option 3: Update Existing Meeting

If you already have a meeting ID:

```python
result = summarize_video(
    video_path="path/to/video.mp4",
    meeting_id="abc-123-uuid"
)
```

## Without Supabase

To use the summarizer **without** Supabase (original behavior):

```python
result = summarize_video(
    video_path="path/to/video.mp4"
    # Don't provide title or meeting_id
)
```

## Database Schema

### meetings table

| Column      | Type    | Example                                  |
|-------------|---------|------------------------------------------|
| id          | UUID    | abc-123-uuid                             |
| title       | Text    | "Q4 Planning Meeting"                    |
| video_url   | Text    | "https://storage.../video.mp4"           |
| consent     | Boolean | true                                     |
| status      | Text    | "processing" → "summarized"              |
| created_at  | Timestamp | 2024-01-15 10:30:00                    |

### summaries table

| Column      | Type    | Description                              |
|-------------|---------|------------------------------------------|
| meeting_id  | UUID    | Foreign key to meetings.id               |
| payload     | JSONB   | Complete summary data                    |
| created_at  | Timestamp | When summary was created               |

## Environment Setup

Ensure your `.env` has:

```env
# Supabase Configuration
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_KEY=[YOUR-ANON-KEY]
SUPABASE_SERVICE_ROLE_KEY=[YOUR-SERVICE-ROLE-KEY]

# Google Gemini (for video processing)
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

## Error Handling

If Supabase is not configured or fails:
- Processing continues normally
- Warning messages printed to stderr
- No meeting record created
- Local files still saved

This ensures the summarizer works even without Supabase.

## See Also

- `example_video_upload.py` - Working examples
- `app/supabase/services/meeting_service.py` - Meeting service API
- `app/supabase/services/summary_service.py` - Summary service API

