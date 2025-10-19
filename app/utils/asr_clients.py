# app/utils/asr_clients.py
import os
import httpx
from typing import Optional

HEADERS_AAI = lambda key: {"authorization": key, "content-type": "application/json"}
BASE_AAI = "https://api.assemblyai.com/v2"

HEADERS_DG = lambda key: {"Authorization": f"Token {key}"}
BASE_DG = "https://api.deepgram.com/v1"

async def start_asr_job(
    media_url: str,
    provider: str,
    meeting_id: str,
    webhook_url: Optional[str] = None,
) -> str:
    """
    Starts an ASR job with the selected provider. Returns provider job_id.
    We attach meeting_id as metadata when supported so the webhook can map it back.
    """
    provider = provider.lower()

    if provider == "assemblyai":
        key = os.getenv("ASSEMBLYAI_API_KEY")
        if not key:
            raise RuntimeError("ASSEMBLYAI_API_KEY missing")
        payload = {
            "audio_url": media_url,
            "speaker_labels": True,
            "language_detection": True,
            "webhook_url": webhook_url,
            "metadata": {"meeting_id": meeting_id},
        }
        async with httpx.AsyncClient(timeout=180) as s:
            r = await s.post(f"{BASE_AAI}/transcribe", headers=HEADERS_AAI(key), json=payload)
            r.raise_for_status()
            return r.json()["id"]

    if provider == "deepgram":
        key = os.getenv("DEEPGRAM_API_KEY")
        if not key:
            raise RuntimeError("DEEPGRAM_API_KEY missing")
        # Deepgram accepts callback via query param or body depending on product;
        # we'll include it in params and provide metadata
        params = {}
        if webhook_url:
            params["callback"] = webhook_url
        json_body = {
            "url": media_url,
            "diarize": True,
            "smart_format": True,
            "punctuate": True,
            "utt_split": True,
            "metadata": {"meeting_id": meeting_id}
        }
        async with httpx.AsyncClient(timeout=180) as s:
            r = await s.post(f"{BASE_DG}/listen", headers=HEADERS_DG(key), params=params, json=json_body)
            r.raise_for_status()
            # Deepgram may return a request_id immediately, or none (if fully async).
            return r.json().get("request_id") or r.headers.get("x-request-id") or meeting_id

    raise ValueError(f"Unsupported ASR provider: {provider}")
