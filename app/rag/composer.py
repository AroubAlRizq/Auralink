import os, httpx, json
from typing import List, Dict
import asyncio
import random

LLM_PROVIDER = os.getenv("LLM_PROVIDER","openai")
LLM_MODEL = os.getenv("LLM_MODEL","gpt-4o-mini")
LLM_API_KEY = os.getenv("LLM_API_KEY")

SYSTEM = ("You are a helpful assistant answering questions about a meeting. "
          "Use ONLY the provided sources. If unsure, say you don't know. "
          "Cite sources with [SPEAKER @ mm:ss–mm:ss]. Be concise.")

def fmt_time(sec: float) -> str:
    m = int(sec // 60); s = int(sec % 60); return f"{m:02d}:{s:02d}"

def build_context(cands: List[Dict]) -> str:
    blocks = []
    for c in cands:
        t = f'{fmt_time(c["start_seconds"])}–{fmt_time(c["end_seconds"])}'
        blocks.append(f'[{c["speaker"]} @ {t}] {c["text"]}')
    return "\n\n".join(blocks)

async def answer_with_citations(question: str, candidates: List[Dict]) -> Dict:
    context = build_context(candidates)
    if LLM_PROVIDER == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        messages = [
            {"role":"system","content":SYSTEM},
            {"role":"user","content": f"Question: {question}\n\nSources:\n{context}\n\nAnswer with citations."}
        ]
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json={"model": LLM_MODEL, "messages": messages, "temperature": 0})
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
    else:
        content = "LLM not configured"
    # Attach raw citations for the UI
    citations = [{
        "speaker": c["speaker"],
        "start": c["start_seconds"],
        "end": c["end_seconds"],
        "text": c["text"]
    } for c in candidates]
    return {"answer": content, "citations": citations}

async def summarize_meeting_json(transcript: str) -> Dict:
    """
    Minimal JSON summarizer using your same LLM provider.
    """
    if LLM_PROVIDER != "openai":
        return {"meeting_id": None, "executive_summary": [], "decisions": [], "action_items": [], "risks": [], "followups": []}

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    prompt = (
        "Summarize the meeting transcript into JSON with keys: "
        "executive_summary (5-10 bullets), decisions (list of {text, timestamp}), "
        "action_items (list of {owner, task, due, timestamp}), risks (list of strings), followups (list of strings). "
        "Return ONLY valid JSON without any markdown formatting or code blocks."
    )
    messages = [
        {"role": "system", "content": "You are a precise meeting summarizer. Return only valid JSON without markdown."},
        {"role": "user", "content": f"{prompt}\n\nTranscript:\n{transcript}"}
    ]
    
    # Retry logic for rate limits
    max_retries = 3
    text = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, headers=headers, json={
                    "model": LLM_MODEL, 
                    "messages": messages, 
                    "temperature": 0,
                    "response_format": {"type": "json_object"}  # Force JSON mode
                })
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                    print(f"Rate limited, waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Fallback response when rate limited
                    return {
                        "executive_summary": ["Meeting summary unavailable due to rate limits"],
                        "decisions": [],
                        "action_items": [],
                        "risks": [],
                        "followups": []
                    }
            else:
                raise
    
    if not text:
        return {
            "executive_summary": ["Failed to generate summary"],
            "decisions": [],
            "action_items": [],
            "risks": [],
            "followups": []
        }
    
    # Clean up markdown code blocks if present
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    if text.startswith("```"):
        text = text[3:]  # Remove ```
    if text.endswith("```"):
        text = text[:-3]  # Remove ```
    text = text.strip()
    
    # Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Raw text: {text[:200]}...")
        data = {
            "executive_summary": [text[:500]],  # Include first 500 chars as fallback
            "decisions": [],
            "action_items": [],
            "risks": [],
            "followups": []
        }
    
    return data