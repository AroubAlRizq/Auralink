# app/utils/asr_clients.py
import os
import httpx

A2_BASE = "https://api.assemblyai.com/v2"
AAI_400_SCHEMA_MSG = "Invalid endpoint schema"


def _is_schema_error(resp_text: str) -> bool:
    if not resp_text:
        return False
    # match common phrasing returned by AAI
    return "Invalid endpoint schema" in resp_text or "refer to documentation" in resp_text


def _headers():
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not set")
    return {"Authorization": api_key, "Accept": "application/json", "Content-Type": "application/json"}


async def _post_transcript(json_payload: dict, *, endpoint: str = "transcript"):
    """
    POST to /v2/<endpoint> with the given JSON payload. Returns (status, text, json or None).
    """
    url = f"{A2_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=_headers(), json=json_payload)
    try:
        data = r.json()
    except Exception:
        data = None
    return r.status_code, r.text, data


async def start_asr_job(
    *,
    media_url: str,
    provider: str,
    meeting_id: str,
    webhook_url: str | None,
):
    """
    Start an ASR job for a remote media URL.

    Strategy:
      1) Try standard payload (speaker_labels + metadata string).
      2) If AAI complains about endpoint schema, retry with MINIMAL payload.
      3) If it still fails, retry against '/transcripts' (plural) with minimal payload.
    """
    provider = (provider or "").lower()
    if provider != "assemblyai":
        raise RuntimeError(f"Unknown/unsupported ASR provider: {provider}")

    # 1) standard payload
    payload_standard = {
        "audio_url": media_url,
        "speaker_labels": True,
        # IMPORTANT: keep metadata strictly a STRING (not an object)
        "metadata": str(meeting_id),
    }
    if webhook_url and webhook_url.startswith("https://"):
        payload_standard["webhook_url"] = webhook_url

    status, text, data = await _post_transcript(payload_standard, endpoint="transcript")
    if status < 400 and isinstance(data, dict) and data.get("id"):
        return data["id"]

    # If it wasn't a schema issue, fail fast with details
    if status >= 400 and not _is_schema_error(text):
        raise RuntimeError(f"AssemblyAI error {status} {text}\nPayload={payload_standard}")

    # 2) minimal payload retry (just audio_url)
    payload_min = {"audio_url": media_url}
    status, text, data = await _post_transcript(payload_min, endpoint="transcript")
    if status < 400 and isinstance(data, dict) and data.get("id"):
        return data["id"]

    # If still a schema error, try the plural endpoint as a final compatibility shim
    if status >= 400 and _is_schema_error(text):
        status, text, data = await _post_transcript(payload_min, endpoint="transcripts")
        if status < 400 and isinstance(data, dict) and data.get("id"):
            return data["id"]

    # Give a very explicit error with the last attempt shown
    raise RuntimeError(
        f"AssemblyAI error {status} {text}\n"
        f"Tried payloads:\n"
        f" 1) {payload_standard}\n"
        f" 2) {payload_min} (endpoint=/transcript)\n"
        f" 3) {payload_min} (endpoint=/transcripts)"
    )