# app/rag/openqa.py
from __future__ import annotations
import os
import httpx

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
GENERAL_LLM = os.getenv("GENERAL_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))

SMALLTALK = {
    "hi", "hello", "hey", "yo", "good morning", "good evening", "good night",
    "how are you", "who are you", "what can you do", "thanks", "thank you",
    "ok", "okay", "cool", "great", "nice", "bye", "goodbye",
}

def _looks_like_smalltalk(q: str) -> bool:
    ql = (q or "").strip().lower()
    if not ql:
        return False
    if ql in SMALLTALK:
        return True
    # very short & generic → likely not about meeting content
    return len(ql) < 16 and all(ch.isalpha() or ch.isspace() for ch in ql)

async def answer_open_domain(question: str, meeting_title: str | None = None) -> str:
    """
    Very small wrapper around OpenAI Chat Completions to answer general questions.
    Keeps it short and neutral; no meeting-specific hallucinations.
    """
    if not OPENAI_KEY:
        return "I can’t access a general model right now (missing OPENAI_API_KEY)."

    system = (
        "You are Auralink's assistant. Answer concisely in 1–3 sentences. "
        "If the user asks for the meeting’s content, say you need the transcript. "
        "Avoid fabricating meeting details."
    )
    if meeting_title:
        system += f" The current meeting title is: {meeting_title}."

    payload = {
        "model": GENERAL_LLM,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        "temperature": 0.3,
    }

    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
    url = f"{OPENAI_BASE}/chat/completions"

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            try:
                err = r.json()
            except Exception:
                err = {"error": r.text}
            return f"[general model error] {err}"
        data = r.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "[general model error] Unexpected response format."

def should_use_openqa(question: str, candidates_count: int, top_score: float | None) -> bool:
    """
    Routing heuristic:
      - smalltalk / trivial → True
      - RAG has no recall or very weak recall → True
      - otherwise → False
    """
    if _looks_like_smalltalk(question):
        return True
    if candidates_count == 0:
        return True
    # If your vector search returns cosine similarity in [0,1], treat < 0.18 as weak.
    # Adjust to your retriever’s scale as needed.
    if top_score is not None and top_score < 0.18:
        return True
    return False