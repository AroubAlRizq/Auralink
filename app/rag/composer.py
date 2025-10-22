# app/rag/composer.py
from __future__ import annotations
import os, json, math, asyncio
from typing import Dict, List, Any, Optional
import httpx

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# ====== Model / runtime config ======
PRIMARY_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
FALLBACK_MODEL = os.getenv("LLM_MODEL_FALLBACK", "").strip() or None
TEMPERATURE = float(os.getenv("SUMMARY_TEMPERATURE", "0"))

# summarization chunking
MAX_CHARS_PER_CHUNK = int(os.getenv("SUMMARY_MAX_CHARS_PER_CHUNK", "8000"))
MAX_CHUNKS = int(os.getenv("SUMMARY_MAX_CHUNKS", "8"))

# retries
RETRY_DELAYS = [0.5, 1.0, 2.0, 4.0, 8.0]


# ---------- shared helpers ----------
def _auth_headers() -> dict:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    org = os.getenv("OPENAI_ORG", "").strip()
    if org:
        hdr["OpenAI-Organization"] = org
    return hdr


async def _chat_once(model: str, messages: List[dict], *, response_json: bool = False, temperature: Optional[float] = None) -> Any:
    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": TEMPERATURE if temperature is None else temperature,
    }
    if response_json:
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENAI_URL, headers=_auth_headers(), json=body)
    r.raise_for_status()
    data = r.json()
    content = (data["choices"][0]["message"]["content"] or "").strip()
    return content


async def _chat_retry(messages: List[dict], *, models: List[str], response_json: bool = False, temperature: Optional[float] = None) -> Any:
    last_err = None
    for model in models:
        for delay in RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                return await _chat_once(model, messages, response_json=response_json, temperature=temperature)
            except httpx.HTTPStatusError as e:
                code = e.response.status_code if e.response else None
                if code in (429, 500, 502, 503):
                    last_err = f"{code}: {e}"
                    continue
                raise
            except Exception as e:
                last_err = str(e)
                continue
    # give up
    if response_json:
        return json.dumps({"_error": last_err or "chat_failed"})
    return f"Sorry, I couldn’t answer just now ({last_err}). Please try again."


# ---------- Summarization (kept from your previous version) ----------
def _normalize_summary(payload: dict) -> dict:
    if not isinstance(payload, dict):
        payload = {}
    exec_sum = payload.get("executive_summary") or payload.get("overview") or payload.get("summary") or ""
    if isinstance(exec_sum, list):
        overview = " ".join([str(x).strip() for x in exec_sum if x])
    else:
        overview = str(exec_sum or "").strip()
    key_points = payload.get("key_points") or payload.get("key_events") or []
    decisions = payload.get("decisions") or []
    action_items = payload.get("action_items") or []
    # force shapes
    key_points = [str(x) for x in key_points] if isinstance(key_points, list) else []
    decisions = [str(x) for x in decisions] if isinstance(decisions, list) else []
    if isinstance(action_items, list):
        norm_ai = []
        for a in action_items:
            if isinstance(a, dict) and "task" in a:
                norm_ai.append({"task": str(a["task"])})
            else:
                norm_ai.append({"task": str(a)})
        action_items = norm_ai
    else:
        action_items = []
    return {
        "overview": overview,
        "key_points": key_points,
        "decisions": decisions,
        "action_items": action_items,
    }


def _prompt_for_chunk(chunk_text: str) -> List[dict]:
    sys = (
        "You are a helpful meeting analyst. Extract a concise summary as JSON with keys: "
        "executive_summary (2–4 sentences), key_points (bulleted items), decisions (bulleted), "
        "action_items (bulleted tasks). Be factual; do not invent content."
    )
    usr = (
        "Transcript segment:\n"
        f"{chunk_text}\n\n"
        "Return ONLY JSON with keys: executive_summary, key_points, decisions, action_items."
    )
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": usr},
    ]


def _prompt_for_merge(chunks_json: List[dict]) -> List[dict]:
    sys = (
        "You are a helpful meeting analyst. You will be given multiple partial JSON summaries "
        "(from different segments of the same meeting). Merge them into ONE coherent JSON with keys: "
        "executive_summary (4–6 sentences overall), key_points, decisions, action_items. "
        "Consolidate duplicates, keep it concise and factual."
    )
    usr = "Partial summaries:\n" + json.dumps(chunks_json, ensure_ascii=False)
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": usr},
    ]


def _split_into_chunks(text: str, max_chars: int, limit_chunks: int) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    parts: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            line = "\n"
        if cur_len + len(line) > max_chars and cur:
            parts.append("\n".join(cur).strip())
            cur, cur_len = [], 0
            if len(parts) >= limit_chunks - 1:
                break
        cur.append(line)
        cur_len += len(line) + 1
    tail_start = sum(len(p) for p in parts)
    rest = text[tail_start:]
    if cur:
        parts.append("\n".join(cur).strip())
    elif rest:
        parts.append(rest.strip())
    if len(parts) > limit_chunks:
        parts = parts[:limit_chunks]
    return [p for p in parts if p]


async def summarize_meeting_json(transcript: str) -> dict:
    models = [PRIMARY_MODEL] + ([FALLBACK_MODEL] if FALLBACK_MODEL else [])

    if len(transcript) <= MAX_CHARS_PER_CHUNK:
        messages = _prompt_for_chunk(transcript)
        content = await _chat_retry(messages, models=models, response_json=True)
        try:
            out = json.loads(content)
        except Exception:
            out = {"executive_summary": content, "key_points": [], "decisions": [], "action_items": []}
        return _normalize_summary(out)

    chunks = _split_into_chunks(transcript, MAX_CHARS_PER_CHUNK, MAX_CHUNKS)
    partials: List[dict] = []
    for ch in chunks:
        m = _prompt_for_chunk(ch)
        content = await _chat_retry(m, models=models, response_json=True)
        try:
            partial = json.loads(content)
        except Exception:
            partial = {"executive_summary": content, "key_points": [], "decisions": [], "action_items": []}
        partials.append(_normalize_summary(partial))

    merge_msgs = _prompt_for_merge(partials)
    merged = await _chat_retry(merge_msgs, models=models, response_json=True)
    try:
        merged_json = json.loads(merged)
    except Exception:
        merged_json = {"executive_summary": merged, "key_points": [], "decisions": [], "action_items": []}
    return _normalize_summary(merged_json)


# ---------- RAG: answer with citations ----------
def _norm_passages(passages: List[Dict[str, Any]], limit: int = 12, max_chars_each: int = 900) -> List[Dict[str, Any]]:
    """Normalize retriever results to {text, speaker?, start_seconds?, end_seconds?, score?}"""
    norm: List[Dict[str, Any]] = []
    for p in passages or []:
        text = (p.get("text") or p.get("chunk") or p.get("content") or "").strip()
        if not text:
            continue
        meta = p.get("meta") or p.get("metadata") or {}
        item = {
            "text": text[:max_chars_each],
            "speaker": meta.get("speaker") or p.get("speaker"),
            "start_seconds": meta.get("start_seconds") or p.get("start_seconds"),
            "end_seconds": meta.get("end_seconds") or p.get("end_seconds"),
            "score": p.get("score"),
        }
        norm.append(item)
        if len(norm) >= limit:
            break
    return norm


def _build_citation_messages(question: str, passages: List[Dict[str, Any]]) -> List[dict]:
    sys = (
        "You are a helpful meeting assistant. Answer ONLY using the provided snippets. "
        "Cite relevant snippets inline as [#] where # is the index in the provided list (1-based). "
        "If the answer is not contained in the snippets, say you don't have enough information."
    )
    indexed = []
    for i, p in enumerate(passages, start=1):
        t = p["text"]
        sp = p.get("speaker")
        ss = p.get("start_seconds")
        es = p.get("end_seconds")
        header = f"[{i}]"
        if sp or ss is not None or es is not None:
            timing = ""
            if ss is not None or es is not None:
                timing = f" {ss:.1f}-{es:.1f}s" if (isinstance(ss, (int,float)) and isinstance(es, (int,float))) else ""
            who = f"{sp}" if sp else "Speaker"
            header += f" {who}{timing}"
        indexed.append(f"{header}: {t}")

    user = (
        "Snippets:\n" + "\n\n".join(indexed) +
        "\n\nQuestion: " + question +
        "\n\nGive a concise answer. Use [#] style citations to support key statements."
    )
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]


async def answer_with_citations(question: str, passages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compose an answer using retrieved passages with inline bracket citations.
    Returns: { "answer": str, "sources": [{t, speaker, text, start_seconds, end_seconds}] }
    """
    models = [PRIMARY_MODEL] + ([FALLBACK_MODEL] if FALLBACK_MODEL else [])
    top = _norm_passages(passages, limit=12, max_chars_each=900)
    if not top:
        return {
            "answer": "Sorry — I couldn't find enough information in this meeting to answer that.",
            "sources": [],
        }

    msgs = _build_citation_messages(question, top)
    answer = await _chat_retry(msgs, models=models, response_json=False, temperature=0.2)
    if not isinstance(answer, str):
        answer = str(answer)

    # build sources list
    sources = []
    for p in top:
        ss = p.get("start_seconds")
        es = p.get("end_seconds")
        t_str = None
        if isinstance(ss, (int, float)) and isinstance(es, (int, float)):
            t_str = f"{ss:.1f}-{es:.1f}s"
        sources.append({
            "t": t_str,
            "speaker": p.get("speaker"),
            "text": p.get("text", ""),
            "start_seconds": ss,
            "end_seconds": es,
            "score": p.get("score"),
        })

    return {"answer": answer.strip(), "sources": sources}