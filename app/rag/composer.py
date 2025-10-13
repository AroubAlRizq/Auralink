import os, httpx
from typing import List, Dict

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

