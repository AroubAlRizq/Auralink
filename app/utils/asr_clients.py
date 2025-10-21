# app/utils/asr_clients.py
import os
import httpx
from typing import Optional
from pathlib import Path

HEADERS_AAI = lambda key: {"authorization": key}
BASE_AAI = "https://api.assemblyai.com/v2"

HEADERS_DG = lambda key: {"Authorization": f"Token {key}"}
BASE_DG = "https://api.deepgram.com/v1"

async def upload_file_to_assemblyai(file_path: str, api_key: str) -> str:
    """
    Upload a local file to AssemblyAI and return the upload URL.
    AssemblyAI requires files to be uploaded to their CDN first.
    """
    print(f"📤 Uploading file to AssemblyAI: {Path(file_path).name}")
    
    async with httpx.AsyncClient(timeout=300) as client:
        with open(file_path, 'rb') as f:
            response = await client.post(
                f"{BASE_AAI}/upload",
                headers=HEADERS_AAI(api_key),
                content=f.read()
            )
            response.raise_for_status()
            upload_url = response.json()["upload_url"]
            print(f"✅ File uploaded successfully")
            return upload_url

async def start_asr_job(
    media_url: str,
    provider: str,
    meeting_id: str,
    webhook_url: Optional[str] = None,
) -> str:
    """
    Starts an ASR job with the selected provider. Returns provider job_id.
    Handles both URLs and local file paths.
    """
    provider = provider.lower()

    if provider == "assemblyai":
        key = os.getenv("ASSEMBLYAI_API_KEY")
        if not key:
            raise RuntimeError("ASSEMBLYAI_API_KEY missing")

        # Check if media_url is a local file path
        if media_url.startswith("file://") or Path(media_url).exists():
            # Remove file:// prefix if present
            file_path = media_url.replace("file://", "")
            
            # Validate file exists
            if not Path(file_path).exists():
                raise RuntimeError(f"File not found: {file_path}")
            
            # Upload file to AssemblyAI first
            media_url = await upload_file_to_assemblyai(file_path, key)

        # Now create transcription job with the URL
        payload = {
            "audio_url": media_url,
            "speaker_labels": True,
            "language_detection": True,
        }
        
        # Only add webhook if it's a valid HTTPS URL
        if webhook_url and webhook_url.startswith("https://"):
            payload["webhook_url"] = webhook_url
        
        print(f"🔧 Creating AssemblyAI transcript job...")
        print(f"   Audio URL: {media_url[:60]}...")
        print(f"   Speaker labels: True")
        print(f"   Webhook: {webhook_url if webhook_url else 'None (will poll manually)'}")

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{BASE_AAI}/transcript",
                headers={**HEADERS_AAI(key), "content-type": "application/json"},
                json=payload
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                raise RuntimeError(f"AssemblyAI API error {response.status_code}: {response.text}")
            
            return response.json()["id"]

    elif provider == "deepgram":
        key = os.getenv("DEEPGRAM_API_KEY")
        if not key:
            raise RuntimeError("DEEPGRAM_API_KEY missing")
        
        # Deepgram also requires URLs, not local files
        if media_url.startswith("file://") or Path(media_url).exists():
            raise RuntimeError(
                "Deepgram requires a public URL. "
                "Please upload your file to a cloud storage service first, "
                "or use AssemblyAI which supports file uploads."
            )
        
        params = {}
        if webhook_url:
            params["callback"] = webhook_url
        
        json_body = {
            "url": media_url,
            "diarize": True,
            "smart_format": True,
            "punctuate": True,
            "utterances": True,
            "metadata": {"meeting_id": meeting_id}
        }
        
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{BASE_DG}/listen",
                headers=HEADERS_DG(key),
                params=params,
                json=json_body
            )
            response.raise_for_status()
            return response.json().get("request_id") or response.headers.get("x-request-id") or meeting_id

    raise ValueError(f"Unsupported ASR provider: {provider}")