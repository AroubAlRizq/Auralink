# app/utils/asr_clients.py
import os
import httpx

A2_BASE = "https://api.assemblyai.com/v2"

def _headers():
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not set")
    return {
        "Authorization": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

async def _create(payload: dict, endpoint: str):
    """POST to /v2/<endpoint> and return (status, text, json|None)."""
    url = f"{A2_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=_headers(), json=payload)
    try:
        data = r.json()
    except Exception:
        data = None
    return r.status_code, r.text, data

def _ok_has_id(status: int, data):
    return status < 400 and isinstance(data, dict) and data.get("id")

async def start_asr_job(
    *,
    media_url: str,
    provider: str,
    meeting_id: str,
    webhook_url: str | None,
):
    """
    Start an AssemblyAI job with adaptive fallbacks:

      1) POST /transcripts (plural), rich payload
      2) POST /transcripts (plural), minimal payload
      3) POST /transcript  (singular), minimal payload
      4) POST /transcript  (singular), rich payload

    We prefer plural, but handle older accounts that only accept singular
    and stricter schemas that only accept minimal payloads.
    """
    if (provider or "").lower() != "assemblyai":
        raise RuntimeError(f"Unknown/unsupported ASR provider: {provider}")

    # Rich payload (may be rejected on older/singular endpoints)
    payload_rich = {
        "audio_url": media_url,
        "speaker_labels": True,
        "metadata": str(meeting_id),  # must be string
    }
    if webhook_url and webhook_url.startswith("https://"):
        payload_rich["webhook_url"] = webhook_url

    # Minimal payload for stricter schemas
    payload_min = {"audio_url": media_url}
    if webhook_url and webhook_url.startswith("https://"):
        payload_min["webhook_url"] = webhook_url

    attempts = [
        ("transcripts", payload_rich,  "plural rich"),
        ("transcripts", payload_min,   "plural minimal"),
        ("transcript",  payload_min,   "singular minimal"),
        ("transcript",  payload_rich,  "singular rich"),
    ]

    last_err = None
    for endpoint, payload, label in attempts:
        status, text, data = await _create(payload, endpoint)
        if _ok_has_id(status, data):
            return data["id"]
        last_err = f"{label}: {status} {text}"

    raise RuntimeError(f"AssemblyAI create transcript failed. Attempts: {last_err}")