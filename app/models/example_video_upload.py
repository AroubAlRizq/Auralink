"""
Example: Upload and process a video with Supabase integration

This shows how to use video_audio_summarizer with automatic Supabase meeting tracking.
"""

from app.models.video_audio_summarizer import summarize_video

def process_video_with_meeting_tracking(
    video_path: str,
    title: str,
    video_url: str = None,
    consent: bool = True
):
    """
    Process a video and automatically create/update meeting record in Supabase.
    
    Args:
        video_path: Path to the video file
        title: Meeting title (e.g., "Q4 Planning Meeting")
        video_url: Public URL where video is stored (optional)
        consent: User consent for recording (default: True)
    
    Returns:
        dict: Processing results including meeting_id
    """
    print(f"Processing video: {title}")
    
    # Call summarize_video with title to enable Supabase integration
    result = summarize_video(
        video_path=video_path,
        title=title,
        video_url=video_url,
        consent=consent,
        workdir=f"./vproc_{title.replace(' ', '_')}"
    )
    
    print(f"\n✅ Processing complete!")
    print(f"   Meeting ID: {result.get('meeting_id', 'N/A')}")
    print(f"   Narration: {result['narration_file']}")
    print(f"   Summary: {result['summary_file']}")
    
    return result


def update_existing_meeting(
    video_path: str,
    meeting_id: str
):
    """
    Process a video and update an existing meeting record.
    
    Args:
        video_path: Path to the video file
        meeting_id: Existing meeting UUID to update
    
    Returns:
        dict: Processing results
    """
    print(f"Updating meeting: {meeting_id}")
    
    result = summarize_video(
        video_path=video_path,
        meeting_id=meeting_id,
        workdir=f"./vproc_{meeting_id}"
    )
    
    print(f"\n✅ Update complete!")
    print(f"   Meeting ID: {result['meeting_id']}")
    
    return result


if __name__ == "__main__":
    # Example 1: Process new video and create meeting record
    result = process_video_with_meeting_tracking(
        video_path="path/to/your/video.mp4",
        title="Q4 Planning Meeting",
        video_url="https://tocyfugfqcvbdemdzpmu.storage.supabase.co/storage/v1/s3",
        consent=True
    )
    
    # Example 2: Update existing meeting (uncomment to use)
    # result = update_existing_meeting(
    #     video_path="path/to/your/video.mp4",
    #     meeting_id="abc-123-uuid"
    # )

