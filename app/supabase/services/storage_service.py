# app/supabase/services/storage_service.py
"""
Supabase Storage service for managing video uploads.
"""

import os
from pathlib import Path
from typing import Optional, Dict
from supabase import Client


class StorageService:
    """Handle video file uploads to Supabase Storage."""
    
    BUCKET_NAME = "videos"
    
    def __init__(self, client: Client):
        self.client = client
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create the videos bucket if it doesn't exist."""
        try:
            # Try to get bucket info
            self.client.storage.get_bucket(self.BUCKET_NAME)
        except Exception:
            # Bucket doesn't exist, create it
            try:
                self.client.storage.create_bucket(
                    self.BUCKET_NAME,
                    options={
                        "public": False,  # Set to True if you want public access
                        "fileSizeLimit": 1024 * 1024 * 500,  # 500MB limit
                        "allowedMimeTypes": [
                            "video/mp4",
                            "video/mpeg",
                            "video/quicktime",
                            "video/x-msvideo",
                            "video/webm"
                        ]
                    }
                )
                print(f"Created storage bucket: {self.BUCKET_NAME}")
            except Exception as e:
                print(f"Warning: Could not create bucket (may already exist): {e}")
    
    def upload_video(
        self,
        file_path: str,
        meeting_id: str,
        original_filename: Optional[str] = None
    ) -> Dict:
        """
        Upload a video file to Supabase Storage.
        
        Args:
            file_path: Local path to the video file
            meeting_id: UUID of the meeting (used for folder organization)
            original_filename: Original filename (optional, uses file_path name if not provided)
        
        Returns:
            Dict with 'path', 'url', and 'size' keys
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        # Use original filename or extract from path
        filename = original_filename or file_path.name
        
        # Organize by meeting_id folder
        storage_path = f"{meeting_id}/{filename}"
        
        # Read file bytes
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        # Upload to Supabase Storage
        try:
            response = self.client.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=file_bytes,
                file_options={
                    "content-type": self._get_mime_type(filename),
                    "upsert": "true"  # Overwrite if exists
                }
            )
            
            # Get public URL (or signed URL if bucket is private)
            if self._is_bucket_public():
                url = self.client.storage.from_(self.BUCKET_NAME).get_public_url(storage_path)
            else:
                # Generate signed URL valid for 1 year
                url = self.client.storage.from_(self.BUCKET_NAME).create_signed_url(
                    storage_path,
                    expires_in=31536000  # 1 year in seconds
                )['signedURL']
            
            return {
                "path": storage_path,
                "url": url,
                "size": len(file_bytes)
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to upload video to Supabase Storage: {e}")
    
    def delete_video(self, storage_path: str) -> bool:
        """Delete a video from storage."""
        try:
            self.client.storage.from_(self.BUCKET_NAME).remove([storage_path])
            return True
        except Exception as e:
            print(f"Warning: Failed to delete video: {e}")
            return False
    
    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Get a signed URL for a video file.
        
        Args:
            storage_path: Path in storage (e.g., "meeting_id/video.mp4")
            expires_in: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Signed URL string
        """
        try:
            result = self.client.storage.from_(self.BUCKET_NAME).create_signed_url(
                storage_path,
                expires_in=expires_in
            )
            return result['signedURL']
        except Exception as e:
            raise RuntimeError(f"Failed to generate signed URL: {e}")
    
    def _get_mime_type(self, filename: str) -> str:
        """Determine MIME type from filename extension."""
        ext = Path(filename).suffix.lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.mpeg': 'video/mpeg',
            '.mpg': 'video/mpeg',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska'
        }
        return mime_types.get(ext, 'video/mp4')
    
    def _is_bucket_public(self) -> bool:
        """Check if the bucket is public."""
        try:
            bucket_info = self.client.storage.get_bucket(self.BUCKET_NAME)
            return bucket_info.get('public', False)
        except Exception:
            return False