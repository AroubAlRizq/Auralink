# app/api/aai_debug.py
from fastapi import APIRouter, HTTPException, Query
import os, httpx

router = APIRouter(tags=["asr"])

A2_BASE = "https://api.assemblyai.com/v2"

@router.get("/aai/job")
async def aai_job(job_id: str = Query(...)):
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(500, "ASSEMBLYAI_API_KEY not set")
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.get(f"{A2_BASE}/transcripts/{job_id}", headers={"Authorization": api_key})
    if r.status_code == 404:
        raise HTTPException(404, "Not found at provider")
    if r.status_code >= 400:
        raise HTTPException(502, f"Provider returned {r.status_code}: {r.text}")
    return r.json()