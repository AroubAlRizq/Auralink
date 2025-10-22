from fastapi import APIRouter, HTTPException
import os, httpx

router = APIRouter(tags=["debug"])
A2_BASE = "https://api.assemblyai.com/v2"

TEST_AUDIO = "https://storage.googleapis.com/aai-web-samples/espn-mlb-clip.mp3"

@router.post("/aai_smoke")
async def aai_smoke():
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")

    headers = {"Authorization": api_key, "Accept": "application/json", "Content-Type": "application/json"}
    payload = {
        "audio_url": TEST_AUDIO,
        "speaker_labels": True,
        "metadata": "smoketest",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{A2_BASE}/transcript", headers=headers, json=payload)
        if r.status_code == 404:
            r = await client.post(f"{A2_BASE}/transcripts", headers=headers, json=payload)

    if r.status_code >= 400:
        raise HTTPException(502, f"AAI smoke failed: {r.status_code}: {r.text}")
    return r.json()