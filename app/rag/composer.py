# app/rag/composer.py
import os, httpx, json

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def _get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    return key

async def summarize_meeting_json(transcript: str) -> dict:
    """
    Calls OpenAI Chat Completions to produce a strict JSON summary.
    """
    if not transcript.strip():
        # Nothing to summarize — return empty but well-formed payload
        return {
            "overview": "",
            "key_points": [],
            "decisions": [],
            "action_items": [],
        }

    api_key = _get_openai_key()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    prompt = (
        "You are a meeting summarizer. Return ONLY strict JSON with keys: "
        "overview (string), key_points (array of strings), decisions (array of strings), "
        "action_items (array of objects with fields owner (string|null), task (string), due (string|null)). "
        "No extra text.\n\nTRANSCRIPT:\n" + transcript
    )

    body = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You return only strict JSON."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(OPENAI_URL, headers=headers, json=body)

    # Raise if non-2xx so we see the *actual* reason in logs
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Surface the exact server message
        raise

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except Exception:
        # If model returned something slightly off, fall back safely
        return {
            "overview": content[:1000],
            "key_points": [],
            "decisions": [],
            "action_items": [],
        }